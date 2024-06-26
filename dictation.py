import base64
import threading
import time
import websockets
import asyncio
import json
import re
import os
import pyaudio
import speech_recognition as sr
from abc import ABC, abstractmethod
from google.cloud import speech_v1p1beta1 as speech
from threading import Timer
from logger import Logger
import random

device_index = 3 # My External USB mic. Use the script in tools to find yours. 

URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

class Dictation(ABC):
    @abstractmethod
    def getDictatedInput(self, device_index, interruptable=False):
        pass

    @abstractmethod
    def done_speaking(self, current_line):
        pass


class StaticGoogleDictation(Dictation):
    def getDictatedInput(self, device_index, interruptable=False):
        Logger.print_debug("Testing audio input access...")
        recognizer = sr.Recognizer()

        with sr.Microphone(device_index=device_index) as source:
            Logger.print_info("Microphone detected.")
            Logger.print_info("Calibrating microphone...")

            recognizer.adjust_for_ambient_noise(source, duration=1)

            Logger.print_info("Go!")

            audio = recognizer.listen(source, phrase_time_limit=50000)
            Logger.print_info("Finished listening.")

            try:
                text = recognizer.recognize_google(audio)
                Logger.print_user_input("You: ", text)
                return text
            except sr.UnknownValueError:
                Logger.print_error("Google Speech Recognition could not understand the audio.")
            except sr.RequestError as e:
                Logger.print_error(f"Could not request results from Google Speech Recognition service; {e}")

    def done_speaking(self, current_line):
        pass

class LiveGoogleDictation(Dictation):
    SILENCE_THRESHOLD = 2.5  # seconds <-- maybe have one threshold for user_turn and a different one for AI_TURN?
    COUNTER = 0

    def __init__(self):
        try:
            self.listening = True
            self.client = speech.SpeechClient()
            self.audio_stream = pyaudio.PyAudio().open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )
            self.stop_words = ["ganglia", "stop", "excuse me"]  # Saying these words will interrupt the AI's turn (TODO move to a config)
        except Exception as e:
            Logger.print_error(f"Error initializing LiveGoogleDictation: {e}")
            raise

    def get_config(self):
        return speech.StreamingRecognitionConfig(
            config=speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="en-US",
                enable_automatic_punctuation=True,
                use_enhanced=True
            ),
            interim_results=True,
        )

    def generate_audio_chunks(self):
        while self.listening == True:
            yield self.audio_stream.read(1024, exception_on_overflow=False)

    def done_speaking(self):
            self.listening = False

    def generate_random_phrase(self):
        # TODO ugh - omjp, this is an abomination. Please move it. We should move this to config and have a teplate with something short and simple.
        #      We could also consider having a subfolder in config called `examples` and put things like this and previous chatgpt and ttv configs in there
        if self.COUNTER % 10 == 0:
            phrases = ["I hear you from the other side...",
            "Speak, mortal.",
            "Whisper your query into the abyss...",
            "I await in the shadows...",
            "Your words echo in the void...",
            "What secrets do you hold?",
            "Your voice summons me...",
            "Dare you speak more?",
            "The darkness listens...",
            "My ears are a portal to the unknown...",
            "Speak, and enter the abyss...",
            "Listening... or maybe lurking.",
            "The night is young, proceed...",
            "You summon me...",
            "I'm lurking in the dark...",
            "Don't be shy, I'm here...",
            "Proceed, if you dare...",
            "What's your dark wish?",
            "I listen as the clock strikes midnight...",
            "Ahh, fresh souls to listen to...",
            "Speak, but tread carefully...",
            "The crypt is open, speak...",
            "Ready for your incantation...",
            "Silence is eerie, isn't it?",
            "Your words echo in my realm...",
            "Listening from the depths...",
            "Speak, I thirst for your words...",
            "I'm right behind you, speak...",
            "The dead don't sleep, neither do I...",
            "Your utterance intrigues me...",
            "I hear you, as does the void...",
            "Echo your words in the eternal darkness...",
            "I'm all fangs, go ahead...",
            "Proceed, I'm dying to hear you...",
            "What's the matter, cat got your tongue?",
            "My ears are as keen as a bat's...",
            "Listening, but not alone...",
            "Speak, for the night wanes...",
            "Dwell deeper, and speak...",
            "Your words are an offering...",
            "The spirits are listening too...",
            "Time waits for no one, speak...",
            "Your voice is a beacon in the dark...",
            "Listening, just a shadow away...",
            "Don't keep me hanging...",
            "I'm all eyes and ears...",
            "What does the night have in store?",
            "Words or screams, I listen to both...",
            "Awaken me with your voice...",
            "I hear you, as does the night..."]

            self.COUNTER += 1
            return random.choice(phrases)
        else:
            self.COUNTER += 1
            return "..."

    def transcribe_stream(self, stream, interruptable=False):
        done_speaking_timer = None
        self.state = 'START'
        finalized_transcript = ''

        # The generator function will continuously yield audio data
        requests = (speech.StreamingRecognizeRequest(audio_content=chunk) for chunk in stream)
        responses = self.client.streaming_recognize(self.get_config(), requests)

        # This block only gets called if speech is found in audio buffer from request above
        for response in responses:

            # Ensure that we have data to process
            if not response.results:
                continue
            result = response.results[0]
            if not result.alternatives:
                continue

            current_input = result.alternatives[0].transcript.strip()

            # Check for stop words in the transcript
            if interruptable:
                for stop_word in self.stop_words:
                    if stop_word in current_input:
                        # We're not recording this part of the conversation, so we can just bail
                        Logger.print_debug(f"Stop word detected in user input: '{current_input}'. Exiting listening thread...")
                        self.done_speaking()
                        return f"{stop_word} " # Exit the loop to stop listening

            # If we receive any new input, cancel the done_speaking_timer
            if done_speaking_timer is not None:
                done_speaking_timer.cancel()

            # This is set when the algo has stopped listening for the current utterance
            is_final = result.is_final

            # Now process the results from the microphone input
            # (the fancy escape sequeces are for terminal cursor and feed control)
            if self.state == 'START':
                Logger.print_user_input(f'\033[K{current_input}\r', end='', flush=True)
                self.state = 'LISTENING'

            elif is_final:
                finalized_transcript += f"{current_input} "
                Logger.print_user_input(f'\033[K{current_input}', flush=True)
                self.state = 'START'
                done_speaking_timer = Timer(self.SILENCE_THRESHOLD, self.done_speaking)
                done_speaking_timer.start()

            elif self.state == 'LISTENING':
                Logger.print_user_input(f'\033[K{current_input}', end='\r', flush=True)

        return finalized_transcript

    def getDictatedInput(self, device_index, interruptable=False):
        # Async function to transcribe speech
        self.listening = True
        transcript = self.transcribe_stream(self.generate_audio_chunks(), interruptable)
        return transcript

class LiveAssemblyAIDictation(Dictation):
    FRAMES_PER_BUFFER = 3200
    RATE = 16000
    ASSEMBLYAI_TOKEN = os.environ.get("ASSEMBLYAI_TOKEN")

    # TODO - make silence threshold configurable?
    SILENCE_THRESHOLD = 1.5  # seconds

    URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

    def __init__(self):
        self.last_call_time = time.time()
        self.last_line = ""
        self.speech_started = False
        self.duration_since_last_detected_change = 0.0
        self.silence_detected = False
        self.audio_detected = False
        self.initialized = False
        self.start_msg_printed = False
        self.first_audio_detected = False
        self.dictation_results = ""

    def callback(self, recognizer, audio):
        data = audio.get_raw_data(convert_rate=self.RATE, convert_width=2)
        return base64.b64encode(data).decode("utf-8")
    
    def speech_start_detected(self, current_line):
        # True if the var is true
        if self.speech_started:
            return True
        
        # When var is false, up to us to decide!
        if current_line:
            # We have input
            self.speech_started = True
            Logger.print_debug("Began detecting speech...")


    def done_speaking(self, current_line):
        global last_call_time
        global last_line
        global initialized
        global dictation_results
        global duration_since_last_detected_change

        done_speaking = False  # init

        # Record the current time
        current_time = time.time()

        if not initialized:
            if current_line != "":
                last_line = current_line
                last_call_time = current_time
                initialized = True
                Logger.print_debug("Initialized and awaiting input...")
                return False
        else:
            if current_line != last_line:
                # There has been a change in the input since the last call
                self.duration_since_last_detected_change = 0
                last_line = current_line
                dictation_results.append(current_line)
            else:
                # New input! Reset duration_since_last_detected_change to 0
                self.duration_since_last_detected_change += current_time - last_call_time

            # Determine if done speaking
            if (initialized and
                current_line == "" and
                self.duration_since_last_detected_change >= self.SILENCE_THRESHOLD):
                done_speaking = True

            # Update the last_call_time and last_line global variables
            last_call_time = current_time
            last_line = current_line

        return done_speaking

    async def send_receive(self, device_index):
        global is_done
        Logger.print_info("\nConnecting to live dictation service...")

        # Put the recognizer and source creation inside the send_receive function
        recognizer = sr.Recognizer()
        source = sr.Microphone(device_index=device_index)


        async with websockets.connect(
            URL,
            extra_headers=(("Authorization", self.ASSEMBLYAI_TOKEN),),
            ping_interval=5,
            ping_timeout=20
        ) as _ws:
            await asyncio.sleep(0.1)
            session_begins = await _ws.recv()
            # print(session_begins)

            async def send():
                is_done = False
                with sr.Microphone(device_index=device_index) as s:
                    recognizer.adjust_for_ambient_noise(s, duration=1)
                    Logger.print_info("Start Talking!")

                    while not is_done:
                        try:
                            audio = recognizer.record(s, duration=0.2)
                            data = self.callback(recognizer, audio)
                            json_data = json.dumps({"audio_data": str(data)})
                            await _ws.send(json_data)
                        except websockets.exceptions.ConnectionClosedError as e:
                            Logger.print_error(e)
                            assert e.code == 4008
                            break
                        except Exception as e:
                            if "(OK)" not in str(e):
                                Logger.print_error("Error in send:", e)
                            break
                        try:
                            await asyncio.sleep(0.01)
                        except Exception as e:
                            Logger.print_error("cancelled:", e)
                            is_done = True
                            break
                return is_done

            async def receive():
                global dictation_results
                global initialized
                dictation_results = []
                is_done = False
                initialized = False
                final_phrases = set() 

                while not is_done:
                    try:
                        result_str = await _ws.recv()
                        if result_str:
                            current_phrase = json.loads(result_str)['text']
                            if current_phrase:
                                # Check to see if we've started processing this input yet
                                if not self.speech_started:
                                    newly_started = self.speech_start_detected(current_phrase)
                                
                                if self.speech_started or newly_started:
                                    Logger.print_user_input(current_phrase)

                            # Send the current phrase to the done_speaking method
                            is_done = self.done_speaking(current_phrase)
                            if is_done:
                                Logger.print_info("Finished listening.")
                                break
                    except websockets.exceptions.ConnectionClosedError as e:
                        Logger.print_error(e)
                        assert e.code == 4008
                        break
                    except Exception as e:
                        Logger.print_error("Error in receive:", e)
                        break

                # Print the final set of complete phrases

                # TODO: update this so it isn't a kludge
                if dictation_results:
                    final_phrases = {phrase for phrase in dictation_results if re.match(r'^[A-Z].*\.$', phrase)}
                else:
                    Logger.print_info("No dictation results collected")
                
                final_phrase = ' '.join(final_phrases)
                return final_phrase

            send_task = asyncio.create_task(send())
            receive_task = asyncio.create_task(receive())

            done, pending = await asyncio.wait([send_task, receive_task], return_when=asyncio.FIRST_COMPLETED)
            
            for task in pending:
                task.cancel()

            if send_task in done:
                send_result = send_task.result()
            else:
                send_result = None

            if receive_task in done:
                receive_result = receive_task.result()
            else:
                receive_result = None

            if isinstance(send_result, Exception):
                Logger.print_error("Error in send_result:", send_result)

            if isinstance(receive_result, Exception):
                Logger.print_error("Error in receive_result:", receive_result)

            # Return the result from the receive() function
            return receive_result

    def getDictatedInput(self, device_index, interruptable=False):
        result = asyncio.run(self.send_receive(device_index))
        return result
