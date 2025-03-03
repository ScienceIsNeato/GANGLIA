# GANGLIA Chatbot Architecture Refactoring

## Overview

This document describes the architecture refactoring for GANGLIA, moving the conversational functionality from the main ganglia.py file into a dedicated module for improved modularity and maintainability.

## Core Components

### User Management (`user_management/`)

Manages user profiles and identity information:

- **UserProfile**: Stores user details and conversation history
- **Preferences**: User-specific settings and history

### Conversational Interface (`conversational_interface.py`)

Manages the conversation with the user:

- **Conversation Class**: Replaces direct chatbot functionality from ganglia.py
- **User Input Processing**: Handles processing of user queries and hotword detection
- **Turn Management**: Handles user and AI turns

### Main Application (`ganglia.py`)

Entry point that initializes and coordinates all components:

- **Component Initialization**: Sets up all necessary objects
- **Conversation Loop**: Manages the main interaction flow

### Text-to-Video Integration (`story_generation_driver.py`)

Manages the process of gathering information for video generation:

- **Story Information Collection**: Gathers story details from the user
- **TTV Configuration Generation**: Creates configuration files for the TTV module
- **Process Management**: Handles the TTV process lifecycle

### Publish-Subscribe System (`pubsub/`)

Enables asynchronous communication between components:

- **Event Publishing**: Components can publish events to notify others
- **Event Subscription**: Components can subscribe to events they're interested in
- **Decoupled Communication**: Allows for modular design with loose coupling

## Functionality

The refactored architecture separates concerns by moving the conversational logic out of ganglia.py into dedicated modules:

1. `conversational_interface.py` handles:
   - Processing user input
   - Generating responses
   - Managing conversation flow and turn-taking
   - Handling TTS output
   - Detecting hotwords and triggering appropriate actions

2. `user_management/user_profile.py` handles:
   - User identification
   - Tracking conversation history
   - Managing user preferences

3. `ganglia.py` handles:
   - Initializing all components
   - Managing the main conversation loop
   - Error handling

4. `story_generation_driver.py` handles:
   - Gathering story information from the user
   - Generating TTV configuration files
   - Managing the TTV process

5. `pubsub/` provides:
   - Event-based communication between components
   - Decoupled architecture for better modularity
   - Asynchronous processing capabilities

## TTV Integration Flow

The Text-to-Video (TTV) integration follows this flow:

1. User mentions "video" which is detected as a hotword
2. The conversation interface triggers the story generation driver
3. The driver publishes events requesting specific information
4. The conversation interface handles these requests and gathers information from the user
5. Once all information is collected, the driver generates a configuration file
6. The TTV process is started in a separate thread
7. The conversation can continue while the video is being generated
8. When the video is complete, the user is notified

## Usage Example

A typical conversation flow:

```
User: "Hi Ganglia!"
Ganglia: "Hi there! How can I help you today?"
User: "What's the weather like today?"
Ganglia: "I don't have access to real-time weather information, but I can help you with other questions."
User: "Tell me a joke"
Ganglia: "Why don't scientists trust atoms? Because they make up everything!"
User: "Can you make a video for me?"
Ganglia: "If you tell me an interesting story, I can try to make a video. Give me some broad strokes and I can fill in the details. What do you have in mind for the protagonist? The conflict? The resolution?"
User: "A cat who wants to catch a laser pointer but can never quite get it"
Ganglia: "Great story idea! Now, what artistic style are you thinking for the visual components? What about music styles for the background music and closing credits?"
User: "Make it anime style with upbeat electronic music"
Ganglia: "Thanks! I'm going to start creating your video now. This will take about 7 minutes to complete. I'll let you know when it's ready. In the meantime, we can continue our conversation. What would you like to talk about?"
User: "Goodbye"
Ganglia: "Goodbye! It was nice chatting with you."
```

## Implementation Notes

- The Conversation class centralizes all conversation-related functionality
- UserProfile maintains conversation state across multiple turns
- Error handling is centralized in the main application
- Hotword detection is integrated into the conversation flow
- The pubsub system enables asynchronous communication between components
- The TTV integration is modular and doesn't block the conversation
