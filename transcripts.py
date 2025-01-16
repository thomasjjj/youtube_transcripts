import logging
import json
import os
from datetime import datetime
from typing import Optional
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Ensure Transcripts folder exists
TRANSCRIPTS_FOLDER = "Transcripts"
os.makedirs(TRANSCRIPTS_FOLDER, exist_ok=True)


def extract_video_id(youtube_url_or_id: str) -> Optional[str]:
    """
    Extracts the video ID from a YouTube URL or returns the ID if already provided.

    Args:
        youtube_url_or_id (str): The YouTube URL or video ID.

    Returns:
        Optional[str]: The video ID if found, or None if extraction fails.
    """
    if len(youtube_url_or_id) == 11 and youtube_url_or_id.isalnum():
        logger.info("Input is a valid YouTube video ID.")
        return youtube_url_or_id

    try:
        parsed_url = urlparse(youtube_url_or_id)

        if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
            query_params = parse_qs(parsed_url.query)
            video_id = query_params.get('v', [None])[0]
            logger.info("Extracted video ID from URL query parameters.")
            return video_id
        elif parsed_url.hostname == 'youtu.be':
            video_id = parsed_url.path.lstrip('/')
            logger.info("Extracted video ID from shortened URL.")
            return video_id
        elif parsed_url.hostname == 'www.youtube.com' and parsed_url.path.startswith('/embed/'):
            video_id = parsed_url.path.split('/')[2]
            logger.info("Extracted video ID from embedded URL.")
            return video_id
        else:
            logger.warning("Unsupported URL format.")
            return None
    except Exception as e:
        logger.error(f"Error parsing URL: {e}")
        return None


def fetch_transcript(input_string: str) -> dict:
    """
    Fetches the transcript of a YouTube video using the youtube-transcript-api.

    Args:
        input_string (str): The YouTube video URL or ID.

    Returns:
        dict: A dictionary containing the transcript and metadata, or an error message.
    """
    video_id = extract_video_id(input_string)
    if not video_id:
        logger.error("Invalid YouTube URL or video ID provided.")
        return {"error": "Invalid YouTube URL or video ID."}

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        logger.info("Successfully fetched transcript in English.")
        transcript_text = '\n'.join([item['text'] for item in transcript])
        return {
            "video_id": video_id,
            "language": "en",
            "transcript": transcript_text,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "date_fetched": datetime.now().isoformat()
        }
    except NoTranscriptFound:
        logger.warning("No English transcript found. Attempting to fetch alternative language transcripts.")
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            available_languages = [t.language for t in transcript_list]
            logger.info(f"Available languages: {', '.join(available_languages)}")
            fallback_transcript = transcript_list.find_transcript(
                [t.language_code for t in transcript_list]
            )
            transcript_text = '\n'.join([item['text'] for item in fallback_transcript.fetch()])
            return {
                "video_id": video_id,
                "language": fallback_transcript.language,
                "transcript": transcript_text,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "date_fetched": datetime.now().isoformat()
            }
        except TranscriptsDisabled:
            logger.error("Transcripts are disabled for this video.")
            return {"error": "Transcripts are disabled for this video.", "video_id": video_id}
        except Exception as e:
            logger.error(f"Error fetching alternative transcript: {e}")
            return {"error": f"Error fetching alternative transcript: {e}", "video_id": video_id}
    except Exception as e:
        logger.error(f"Error fetching transcript: {e}")
        return {"error": f"Error fetching transcript: {e}", "video_id": video_id}


def save_transcript_to_json(data: dict) -> None:
    """
    Saves the transcript and metadata to a JSON file in the Transcripts folder.

    Args:
        data (dict): The transcript data and metadata.

    Returns:
        None
    """
    video_id = data.get("video_id", "unknown")
    filename = os.path.join(TRANSCRIPTS_FOLDER, f"{video_id}.json")
    try:
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving transcript to file: {e}")


if __name__ == "__main__":
    while True:
        try:
            input_string = input("\nEnter YouTube video URL or ID (or 'exit' to quit): ").strip()
            if input_string.lower() == 'exit':
                logger.info("Exiting the program.")
                break

            transcript_data = fetch_transcript(input_string)
            save_transcript_to_json(transcript_data)

            if "transcript" in transcript_data:
                print("\nTranscript:")
                print(transcript_data["transcript"])
        except KeyboardInterrupt:
            logger.info("Program interrupted by user.")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
