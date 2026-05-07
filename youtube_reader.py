from youtube_transcript_api import YouTubeTranscriptApi
import re


def extract_video_id(url):

    if "v=" in url:
        return url.split("v=")[1].split("&")[0]

    if "youtu.be" in url:
        return url.split("/")[-1].split("?")[0]

    raise ValueError("Invalid YouTube URL")


def read_youtube(url):

    video_id = extract_video_id(url)

    try:

        # NEW API style (v1.x)
        transcript = YouTubeTranscriptApi().fetch(video_id)

    except Exception:

        # fallback attempt
        transcript = YouTubeTranscriptApi().fetch(video_id, languages=['en','hi'])

    text = " ".join([x.text for x in transcript])

    # clean timestamps
    text = re.sub(r'\d{1,2}:\d{2}', '', text)

    return text