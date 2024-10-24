import json
import os
import openai
import time

import requests
from logger import Logger

def generate_filtered_story(context, style, story_title, query_dispatcher):
    """
    Generates a filtered story based on the provided context and style using ChatGPT.
    
    Args:
        context (str): The context for the story.
        style (str): The style of the story.
        story_title (str): The title of the story.
        query_dispatcher: An instance of the query dispatcher to send the query to ChatGPT.

    Returns:
        str: Generated filtered story in JSON format.
    """
    Logger.print_info("Generating filtered story with ChatGPT.")
    
    prompt = (
        f"I'm about to send this text to DALLE-3 as the input for a movie poster image, but I'm worried about the input not passing the content filters in place by openai. Could you tweak this to ensure that it will pass the filters? Create a filtered story titled '{story_title}' with the style of {style} and the following context:\n\n"
        f"{context}\n\n"
        "Ensure that the generated story is appropriate for all audiences and does not contain any sensitive or inappropriate content.\n\n"
        "Please also rewrite any sections containing PII so that only publicly available information is included.\n\n"
        "Please return the filtered story in the following JSON format:\n"
        "{\n"
        "  \"style\": \"<insert style here>\",\n"
        "  \"title\": \"<insert title here>\",\n"
        "  \"story\": \"<insert filtered story here>\"\n"
        "}"
    )

    try:
        response = query_dispatcher.sendQuery(prompt)
        print("Response for filtered story: " + response)
        
        # Parse the response to extract the filtered story
        response_json = json.loads(response)

        filtered_style = response_json["style"]
        filtered_title = response_json["title"]
        filtered_story = response_json["story"]

        if filtered_story == "No story generated":
            Logger.print_error("Failed to generate filtered story - error in response format. Response: " + response)

        Logger.print_info(f"Generated filtered story: {filtered_story}")
        return json.dumps({
            "style": filtered_style,
            "title": filtered_title,
            "story": filtered_story
        })
    except Exception as e:
        Logger.print_error(f"Error generating filtered story: {e}")
        return json.dumps({
            "style": style,
            "title": story_title,
            "story": "No story generated"
        })

def generate_movie_poster(filtered_story_json, style, story_title, query_dispatcher, retries=5, wait_time=60):
    try:
        filtered_story = json.loads(filtered_story_json)
    except json.JSONDecodeError:
        Logger.print_error("Filtered story is not in valid JSON format")
        return None
    
    filtered_context = filtered_story.get("story", "")
    if not filtered_context:
        Logger.print_error("Filtered story does not contain a story")
        return None

    prompt = f"Create a movie poster for the story titled '{story_title}' with the style of {style} and context: {filtered_context}."
    
    for attempt in range(retries):
        try:
            response = openai.Image.create(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1
            )
            if response.data:
                image_url = response['data'][0]['url']
                filename = "/tmp/GANGLIA/ttv/movie_poster.png"
                save_image_without_caption(image_url, filename)
                return filename
            else:
                Logger.print_error(f"No image was returned for the movie poster.")
                return None
        except Exception as e:
            if 'Rate limit exceeded' in str(e):
                Logger.print_warning(f"Rate limit exceeded. Retrying in {wait_time} seconds... (Attempt {attempt + 1} of {retries})")
                time.sleep(wait_time)
            else:
                Logger.print_error(f"An error occurred while generating the movie poster: {e}")
                return None
    Logger.print_error(f"Failed to generate movie poster after {retries} attempts due to rate limiting.")
    return None

def filter_text(sentence, context, style, query_dispatcher, retries=5, wait_time=60):
    Logger.print_debug(f"Filtering text to pass content filters: '{sentence}' with context '{context}' and style '{style}'")

    prompt = (
        f"Please filter this text to ensure it passes content filters for generating an image:\n\n"
        f"Sentence: {sentence}\n"
        f"Context: {context}\n"
        f"Style: {style}\n\n"
        "Please ensure that the filtered text does not contain any sensitive or inappropriate content.\n\n"
        "Please return the filtered story in the following JSON format:\n"
        "{\n"
        "  \"text\": \"<insert result here>\"\n"
        "}"
    )

    for attempt in range(retries):
        try:
            response = query_dispatcher.sendQuery(prompt)
            response_json = json.loads(response)

            filtered_sentence = response_json.get("text", sentence)  # Fallback to original sentence if key is not found
            Logger.print_debug(f"Filtered sentence: {filtered_sentence}")

            return {"text": filtered_sentence}
        except Exception as e:
            if 'Rate limit exceeded' in str(e):
                Logger.print_warning(f"Rate limit exceeded while filtering text. Retrying in {wait_time} seconds... (Attempt {attempt + 1} of {retries})")
                time.sleep(wait_time)
            else:
                Logger.print_error(f"Error filtering text: {e}")
                return {"text": sentence}  # Fallback to original sentence in case of other errors

    Logger.print_error(f"Failed to filter text after {retries} attempts due to rate limiting.")
    return {"text": sentence}  # Fallback to original sentence after retries


def save_image_without_caption(image_url, filename):
    response = requests.get(image_url)
    if response.status_code == 200:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'wb') as file:
            file.write(response.content)
    Logger.print_info(f"Movie poster saved to {filename}")
