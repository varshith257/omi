from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Structured(BaseModel):
    title: str
    overview: str
    emoji: str = ''
    category: str = 'other'


class ActionItem(BaseModel):
    description: str


class Event(BaseModel):
    title: str
    start: datetime
    duration: int
    description: Optional[str] = ''
    created: bool = False


class MemoryPhoto(BaseModel):
    base64: str
    description: str


class PluginResult(BaseModel):
    plugin_id: Optional[str]
    content: str


class TranscriptSegment(BaseModel):
    text: str
    speaker: Optional[str] = 'SPEAKER_00'
    speaker_id: Optional[int] = None
    is_user: bool
    person_id: Optional[str] = None
    start: float
    end: float

    def __init__(self, **data):
        super().__init__(**data)
        self.speaker_id = int(self.speaker.split('_')[1]) if self.speaker else 0

    def get_timestamp_string(self):
        start_duration = timedelta(seconds=int(self.start))
        end_duration = timedelta(seconds=int(self.end))
        return f'{str(start_duration).split(".")[0]} - {str(end_duration).split(".")[0]}'

    @staticmethod
    def segments_as_string(segments, include_timestamps=False, user_name: str = None):
        if not user_name:
            user_name = 'User'
        transcript = ''
        include_timestamps = include_timestamps and TranscriptSegment.can_display_seconds(segments)
        for segment in segments:
            segment_text = segment.text.strip()
            timestamp_str = f'[{segment.get_timestamp_string()}] ' if include_timestamps else ''
            transcript += f'{timestamp_str}{user_name if segment.is_user else f"Speaker {segment.speaker_id}"}: {segment_text}\n\n'
        return transcript.strip()

    @staticmethod
    def combine_segments(segments: [], new_segments: [], delta_seconds: int = 0):
        if not new_segments or len(new_segments) == 0:
            return segments

        joined_similar_segments = []
        for new_segment in new_segments:
            if delta_seconds > 0:
                new_segment.start += delta_seconds
                new_segment.end += delta_seconds

            if (joined_similar_segments and
                    (joined_similar_segments[-1].speaker == new_segment.speaker or
                     (joined_similar_segments[-1].is_user and new_segment.is_user))):
                joined_similar_segments[-1].text += f' {new_segment.text}'
                joined_similar_segments[-1].end = new_segment.end
            else:
                joined_similar_segments.append(new_segment)

        if (segments and
                (segments[-1].speaker == joined_similar_segments[0].speaker or
                 (segments[-1].is_user and joined_similar_segments[0].is_user)) and
                (joined_similar_segments[0].start - segments[-1].end < 30)):
            segments[-1].text += f' {joined_similar_segments[0].text}'
            segments[-1].end = joined_similar_segments[0].end
            joined_similar_segments.pop(0)

        segments.extend(joined_similar_segments)

        # Speechmatics specific issue with punctuation
        for i, segment in enumerate(segments):
            segments[i].text = (
                segments[i].text.strip()
                .replace('  ', '')
                .replace(' ,', ',')
                .replace(' .', '.')
                .replace(' ?', '?')
            )
        return segments

    @staticmethod
    def can_display_seconds(segments):
        for i in range(len(segments)):
            for j in range(i + 1, len(segments)):
                if segments[i].start > segments[j].end or segments[i].end > segments[j].start:
                    return False
        return True


class Memory(BaseModel):
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    transcript_segments: List[TranscriptSegment] = []
    photos: Optional[List[MemoryPhoto]] = []
    # recordingFilePath: Optional[str] = None
    # recordingFileBase64: Optional[str] = None
    structured: Structured
    plugins_results: List[PluginResult] = []
    discarded: bool

    def get_transcript(self, include_timestamps: bool = False) -> str:
        # Warn: missing transcript for workflow source
        return TranscriptSegment.segments_as_string(self.transcript_segments, include_timestamps=include_timestamps)


class Geolocation(BaseModel):
    google_place_id: Optional[str] = None
    latitude: float
    longitude: float
    address: Optional[str] = None
    location_type: Optional[str] = None


class MemorySource(str, Enum):
    friend = 'friend'
    omi = 'omi'
    openglass = 'openglass'
    screenpipe = 'screenpipe'
    workflow = 'workflow'


class ExternalIntegrationMemorySource(str, Enum):
    audio = 'audio_transcript'
    other = 'other_text'


class ExternalIntegrationCreateMemory(BaseModel):
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    text: str
    text_source: ExternalIntegrationMemorySource = ExternalIntegrationMemorySource.audio
    language: Optional[str] = None
    geolocation: Optional[Geolocation] = None


class EndpointResponse(BaseModel):
    message: str = Field(description="A short message to be sent as notification to the user, if needed.", default='')


class RealtimePluginRequest(BaseModel):
    session_id: str
    segments: List[TranscriptSegment]


class ProactiveNotificationContextFitlersResponse(BaseModel):
    people: List[str] = Field(description="A list of people. ", default=[])
    entities: List[str] = Field(description="A list of entity. ", default=[])
    topics: List[str] = Field(description="A list of topic. ", default=[])

class ProactiveNotificationContextResponse(BaseModel):
    question: str = Field(description="A question to query the embeded vector database.", default='')
    filters: ProactiveNotificationContextFitlersResponse = Field(description="Filter options to query the embeded vector database. ", default=None)

class ProactiveNotificationResponse(BaseModel):
    prompt: str = Field(description="A prompt or a template with the parameters such as {{user_name}} {{user_facts}}.", default='')
    params: List[str] = Field(description="A list of string that match with proactive notification scopes. ", default=[])
    context: ProactiveNotificationContextResponse = Field(description="An object to guide the system in retrieving the users context", default=None)

class ProactiveNotificationEndpointResponse(BaseModel):
    message: str = Field(description="A short message to be sent as notification to the user, if needed.", default='')
    notification: ProactiveNotificationResponse = Field(description="An object to guide the system in generating the proactive notification", default=None)
