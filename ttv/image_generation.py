import json
import os
import openai
import requests
from PIL import Image, ImageDraw, ImageFont
import textwrap
from datetime import datetime
from logger import Logger
import time

from ttv.story_generation import filter_text

def generate_image(sentence, context, style, image_index, total_images, query_dispatcher, retries=5, wait_time=60):
    Logger.print_debug(f"Generating image for: '{sentence}' using a style of '{style}' DALL·E 3")

    filtered_response = filter_text(sentence, context, style, query_dispatcher, retries, wait_time)
    filtered_sentence = filtered_response["text"]

    prompt = f"With the context of: {context}. Create an image that matches the description: '{filtered_sentence}', while keeping the style of {style}. Please focus on the visual elements only and do not include any text in the image.\n\n"
    
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
                filename = f"/tmp/GANGLIA/ttv/image_{image_index}.png"
                save_image_with_caption(image_url, filename, sentence, image_index, total_images)
                return filename, True
            else:
                Logger.print_error(f"No image was returned for the sentence: '{sentence}'")
                return None, False
        except Exception as e:
            if 'Rate limit exceeded' in str(e):
                Logger.print_warning(f"Rate limit exceeded. Retrying in {wait_time} seconds... (Attempt {attempt + 1} of {retries})")
                time.sleep(wait_time)
            else:
                Logger.print_error(f"An error occurred while generating the image: {e}")
                return None, False

    Logger.print_error(f"Failed to generate image after {retries} attempts due to rate limiting.")
    return None, False

def save_image_with_caption(image_url, filename, caption, current_step, total_steps):
    start_time = datetime.now()
    Logger.print_info(f"Starting to save image with caption: '{caption}' to {filename}")
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    download_start_time = datetime.now()
    response = requests.get(image_url)
    if response.status_code == 200:
        with open(filename, 'wb') as file:
            file.write(response.content)
    download_end_time = datetime.now()
    Logger.print_info(f"Image downloaded in {(download_end_time - download_start_time).total_seconds()} seconds.")
    image = Image.open(filename)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("Arial.ttf", 20)
    margin = 10
    max_width = image.width - 2 * margin
    wrapped_text = textwrap.fill(caption, width=40)
    wrapped_text += f" ({current_step}/{total_steps})"
    text_size = draw.textsize(wrapped_text, font=font)
    text_height = text_size[1] * wrapped_text.count('\n') + margin * (wrapped_text.count('\n') + 1)
    new_image_height = image.height + text_height + margin * 2
    new_image = Image.new("RGB", (image.width, new_image_height), "white")
    new_image.paste(image, (0, 0))
    draw = ImageDraw.Draw(new_image)
    draw.multiline_text((margin, image.height + margin), wrapped_text, fill="black", font=font, spacing=5)
    saving_start_time = datetime.now()
    new_image.save(filename)
    saving_end_time = datetime.now()
    Logger.print_info(f"Image saved in {(saving_end_time - saving_start_time).total_seconds()} seconds.")
    end_time = datetime.now()
    Logger.print_info(f"Total time to save image with caption: {(end_time - start_time).total_seconds()} seconds. Saved to {filename}")

def generate_blank_image(sentence, image_index):
    blank_image = Image.new('RGB', (1024, 1024), 'white')
    draw = ImageDraw.Draw(blank_image)
    font = ImageFont.truetype("Arial.ttf", 36)
    draw.text((20, 20), sentence, fill='black', font=font)
    blank_filename = f"/tmp/GANGLIA/ttv/blank_image_{image_index}.png"
    os.makedirs(os.path.dirname(blank_filename), exist_ok=True)
    blank_image.save(blank_filename)
    return blank_filename

def save_image_without_caption(image_url, filename):
    response = requests.get(image_url)
    if response.status_code == 200:
        with open(filename, 'wb') as file:
            file.write(response.content)
    Logger.print_info(f"Movie poster saved to {filename}")

def generate_image_for_sentence(sentence, context, style, image_index, total_images, query_dispatcher):
    filename, success = generate_image(sentence, context, style, image_index, total_images, query_dispatcher=query_dispatcher)
    if not success:
        Logger.print_error(f"Image generation failed for: '{sentence}'. Generating blank image.")
        return generate_blank_image(sentence, image_index)
    return filename
