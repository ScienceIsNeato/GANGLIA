# Debugging Instructions for TTV Hotword Issue

## Setup

1. Open VS Code and load the GANGLIA project
2. Make sure you have the Python extension installed
3. Open the Debug view (Ctrl+Shift+D or Cmd+Shift+D)
4. Select "Python: GANGLIA Conversation" from the dropdown menu

## Breakpoints to Set

Set breakpoints at the following locations to trace the flow of execution when a hotword is detected during the TTV process:

### In `conversational_interface.py`:

1. In the `process_user_input` method:
   - Line where hotwords are detected: `hotword_detected, hotword_phrase = self.hotword_manager.detect_hotwords(...)`
   - Line where TTV state is logged: `Logger.print_debug(f"TTV state: waiting_for_info=...`
   - Line where TTV info response is handled: `if self.ttv_handler.is_waiting_for_ttv_info():`
   - Line where TTV hotword is handled: `elif hotword_detected and any(keyword in user_input.lower() for keyword in ["video", "ttv"]) and not self.ttv_handler.is_in_ttv_process():`

### In `ttv_conversation_handler.py`:

1. In the `is_waiting_for_ttv_info` method:
   - Line where it returns: `return self.waiting_for_ttv_info`

2. In the `is_in_ttv_process` method:
   - Line where it returns: `return (self.waiting_for_ttv_info or ...`

3. In the `handle_ttv_info_response` method:
   - Line where it checks if the response is valid: `is_valid = self._is_valid_ttv_response(user_input, query_dispatcher)`
   - Line where it publishes the event: `self.pubsub.publish(event)`
   - Line where it resets the waiting state: `self.waiting_for_ttv_info = False`

### In `hotwords.py`:

1. In the `detect_hotwords` method:
   - Line where it checks if a hotword is in the prompt: `if hotword in prompt:`
   - Line where it calls the callback function: `response = callback(context)`

## Debugging Steps

1. Start the debugger by clicking the green play button
2. When GANGLIA starts, begin the conversation
3. Say "Let's make a video" to trigger the TTV process
4. When prompted for a story idea, include the word "video" in your response
5. Observe the execution flow through the breakpoints
6. Pay attention to the values of:
   - `self.waiting_for_ttv_info`
   - `self.ttv_process_running`
   - `self.ttv_handler.is_in_ttv_process()`
   - `hotword_detected`
   - `user_input`

## Expected Behavior

With the fixes we've implemented:
1. When you say "Let's make a video", the TTV process should start
2. When you include "video" in your story idea, it should NOT restart the TTV process
3. The `is_in_ttv_process()` method should return `True` during the TTV data collection
4. The condition `hotword_detected and any(keyword in user_input.lower() for keyword in ["video", "ttv"]) and not self.ttv_handler.is_in_ttv_process()` should evaluate to `False`

This will help you confirm that our fix is working correctly and that the TTV process is not being restarted when "video" is mentioned during data collection.
