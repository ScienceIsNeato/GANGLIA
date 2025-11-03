# GANGLIA TTS & Conversational AI Modernization Plan

> **Project Overview**: Modernize GANGLIA from hardcoded quest system + Google TTS to dynamic AI conversation + OpenAI TTS, with optional custom model integration.

## 🎯 Strategic Vision

Transform GANGLIA from a rigid, hardcoded Halloween assistant into a dynamic, AI-powered conversational experience while maintaining its ghastly, demonic character and quest functionality.

### Current State
- **Conversation**: Hardcoded keyword detection with static responses
- **TTS**: Google Cloud Text-to-Speech with limited voice options
- **Quest System**: Manual response mapping for quest fragments
- **Architecture**: Monolithic with tight coupling between components

### Target State
- **Conversation**: Dynamic AI responses with GANGLIA personality baked in
- **TTS**: OpenAI TTS with demonic voice effects and superior quality
- **Quest System**: Natural language quest interactions
- **Architecture**: Modular, hybrid system with local + cloud capabilities

---

## 🚀 Implementation Roadmap

### Phase 1: OpenAI TTS Foundation (Weeks 1-2)
**Objective**: Replace Google TTS with OpenAI TTS while maintaining backward compatibility

#### 1.1 Voice Research & Selection
- **Target Voices**: Onyx (deep masculine), Echo (resonant), Fable (theatrical)
- **Audio Effects Pipeline**: Pitch shifting (-300), reverb (50), chorus effects
- **Character Alignment**: Test voices against GANGLIA's "ghastly demonic" persona

#### 1.2 Architecture Design
```python
# New TTS Interface Design
class OpenAITTS(TextToSpeech):
    def __init__(self, voice="onyx", enable_effects=True):
        self.client = OpenAI()
        self.voice = voice
        self.effects_processor = AudioEffectsProcessor()

    def convert_text_to_speech(self, text, voice_id=None, thread_id=None):
        # Maintain existing interface signature
        # Add audio post-processing for demonic effects
        pass
```

#### 1.3 Configuration Strategy
```json
{
  "tts": {
    "provider": "openai",  // "google" for fallback
    "openai": {
      "voice": "onyx",
      "model": "tts-1-hd",
      "effects": {
        "pitch_shift": -300,
        "reverb": 50,
        "enable_demonic_processing": true
      }
    },
    "voice_mapping": {
      "en-US-Wavenet-D": "onyx"  // Google -> OpenAI mapping
    }
  }
}
```

#### 1.4 Implementation Tasks
- [ ] Create `OpenAITTS` class in `tts.py`
- [ ] Implement audio effects processing pipeline
- [ ] Update `parse_tts_interface()` in `parse_inputs.py`
- [ ] Add configuration management for voice selection
- [ ] Create voice comparison testing framework
- [ ] Update documentation and deployment guides

#### 1.5 Testing Strategy
- **Unit Tests**: OpenAI TTS class functionality
- **Integration Tests**: Full conversation flow with new TTS
- **Voice Quality Tests**: A/B comparison with current Google TTS
- **Character Tests**: Verify demonic voice effects maintain GANGLIA persona

---

### Phase 2: Custom Model Intelligence (Weeks 3-4)
**Objective**: Train and deploy local GANGLIA-specific conversational model

#### 2.1 Training Data Preparation
**Data Sources**:
- Current `ganglia_config.json` personality context (27 lines)
- Quest system responses and fragment mappings
- Halloween party context and neighborhood lore
- Hardcoded hotword responses converted to conversation examples

**Training Format**:
```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are GANGLIA, the Fallen King of Halloween. You live in a coffin with an animatronic skull..."
    },
    {
      "role": "user",
      "content": "Tell me about the quest"
    },
    {
      "role": "assistant",
      "content": "Ah, you're ready to assist me in unlocking my hidden potential! Please take a map from above me..."
    }
  ]
}
```

#### 2.2 Model Training Pipeline
- **Base Model**: Llama 3.2 7B (optimal size for local deployment)
- **Fine-tuning Method**: LoRA (Low-Rank Adaptation) for efficiency
- **Training Platform**: Google Colab (free tier, 15GB VRAM)
- **Training Duration**: ~2-4 hours depending on dataset size
- **Validation**: Quest response accuracy, personality consistency

#### 2.3 Local Deployment Strategy
```python
# Local Model Integration
class LocalGangliaDispatcher(ChatGPTQueryDispatcher):
    def __init__(self):
        self.ollama_client = ollama.Client()
        self.model_name = "ganglia-halloween-7b"
        self.fallback_client = OpenAI()  # For complex tasks

    def send_query(self, user_input):
        try:
            return self.ollama_client.generate(
                model=self.model_name,
                prompt=user_input
            )
        except Exception:
            # Fallback to OpenAI for complex queries
            return self.fallback_client.chat.completions.create(...)
```

#### 2.4 Implementation Tasks
- [ ] Extract and format GANGLIA training data
- [ ] Set up Google Colab training environment
- [ ] Implement LoRA fine-tuning pipeline
- [ ] Create model evaluation framework
- [ ] Set up local Ollama deployment
- [ ] Implement `LocalGangliaDispatcher` class
- [ ] Create model management utilities (download, update, health)

---

### Phase 3: Hybrid System Integration (Weeks 5-6)
**Objective**: Combine OpenAI TTS + Custom Model for optimal experience

#### 3.1 Hybrid Architecture
```
User Input → LocalGangliaDispatcher → Response → OpenAI TTS → Audio Effects → GANGLIA Voice
     ↓                                    ↓
Complex Tasks → OpenAI API (fallback)    Audio Post-Processing Pipeline
```

#### 3.2 Intelligent Routing Logic
```python
class HybridGangliaSystem:
    def route_query(self, user_input):
        if self.is_quest_related(user_input):
            return self.local_model.send_query(user_input)
        elif self.is_complex_reasoning(user_input):
            return self.openai_fallback.send_query(user_input)
        elif self.is_ttv_request(user_input):
            return self.hybrid_ttv_pipeline(user_input)
        else:
            return self.local_model.send_query(user_input)
```

#### 3.3 Performance Optimization
- **Target Latency**: < 2 seconds for 95% of queries
- **Memory Usage**: < 8GB RAM for local model
- **Cost Optimization**: 50% reduction in API costs
- **Graceful Degradation**: Fallback strategies for hardware limitations

#### 3.4 Implementation Tasks
- [ ] Design hybrid routing logic
- [ ] Implement performance monitoring
- [ ] Create cost tracking and optimization
- [ ] Build comprehensive error handling
- [ ] Implement health checks and fallbacks
- [ ] Create end-to-end testing suite

---

### Phase 4: Enterprise Hardening (Weeks 7-8)
**Objective**: Convert MVP into production-ready, maintainable system

#### 4.1 Code Quality & Architecture
- **Dependency Injection**: All TTS/model providers configurable
- **Configuration Management**: Centralized, environment-specific configs
- **Error Handling**: Comprehensive logging and graceful degradation
- **API Management**: Rate limiting, retry logic, circuit breakers
- **Monitoring**: Health checks, performance metrics, alerting

#### 4.2 Advanced Features
- **Model Versioning**: Rollback capability for model updates
- **A/B Testing**: Framework for voice/model combinations
- **Dynamic Effects**: Context-aware audio processing
- **Multi-language**: Foundation for future language support

#### 4.3 Implementation Tasks
- [ ] Refactor for dependency injection pattern
- [ ] Implement comprehensive configuration system
- [ ] Add monitoring and alerting infrastructure
- [ ] Create automated testing pipeline
- [ ] Write deployment and operational guides
- [ ] Implement model versioning system

---

## 📊 Success Metrics

### Technical KPIs
| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Response Latency | ~3-5s | <2s | 95th percentile |
| Quest Accuracy | 100% (hardcoded) | >90% | Natural language eval |
| Error Rate | ~2% | <1% | Production monitoring |
| API Cost | $X/month | <50% current | Monthly billing |

### User Experience KPIs
| Metric | Target | Measurement |
|--------|--------|-------------|
| Voice Quality | >8/10 | Subjective rating |
| Conversation Naturalness | >8/10 | User feedback |
| Quest Completion Rate | >95% | Halloween party metrics |
| System Uptime | >99.9% | Production monitoring |

### Business KPIs
| Metric | Target | Measurement |
|--------|--------|-------------|
| Development Velocity | +50% | Feature delivery time |
| Maintenance Cost | -30% | Engineering hours |
| Extensibility | Easy quest additions | Time to add new content |

---

## 🎃 Halloween Party Deployment Strategy

### Pre-Party Testing (2 weeks before)
- [ ] Full system integration testing
- [ ] Voice quality validation with party attendees
- [ ] Quest flow testing with sample users
- [ ] Performance testing under load
- [ ] Backup system preparation

### Party Day Operations
- [ ] System health monitoring dashboard
- [ ] Real-time performance metrics
- [ ] Immediate fallback to stable system if issues
- [ ] Live audio quality monitoring
- [ ] Guest feedback collection system

### Post-Party Analysis
- [ ] Performance metrics analysis
- [ ] User feedback compilation
- [ ] System reliability assessment
- [ ] Cost analysis and optimization opportunities

---

## 🔧 Technical Implementation Details

### Current Architecture Analysis
```
ganglia.py → initialize_components() → parse_tts_interface() → GoogleTTS
                                   → ChatGPTQueryDispatcher
                                   → Conversation → process_user_input()
```

### Target Architecture
```
ganglia.py → initialize_components() → parse_tts_interface() → OpenAITTS
                                   → HybridGangliaDispatcher → LocalModel + OpenAI
                                   → Conversation → intelligent_routing()
```

### Key Integration Points
1. **TTS Interface**: `TextToSpeech` abstract base class (no changes needed)
2. **Query Dispatcher**: `ChatGPTQueryDispatcher` interface (extend, don't replace)
3. **Configuration**: `ganglia_config.json` (extend with new sections)
4. **Conversation**: `Conversation` class (minimal changes, dependency injection)

### Risk Mitigation
- **Backward Compatibility**: All existing interfaces maintained
- **Graceful Degradation**: Fallback to current system if new components fail
- **Incremental Deployment**: Each phase can be deployed independently
- **Rollback Strategy**: Quick revert to previous stable state

---

## 💰 Cost Analysis

### Current Costs (Monthly)
- **OpenAI API**: ~$X (gpt-4o-mini calls)
- **Google Cloud TTS**: ~$Y
- **Infrastructure**: Minimal (local deployment)

### Projected Costs (Monthly)
- **OpenAI TTS**: ~$15/1M characters
- **Local Model**: $0 (one-time training ~$0-100)
- **Fallback OpenAI**: <50% current usage
- **Infrastructure**: Minimal increase

### ROI Analysis
- **One-time Training**: $0-100 (Google Colab free tier)
- **Monthly Savings**: ~40-60% reduction in API costs
- **Development Efficiency**: +50% faster feature development
- **Maintenance Reduction**: -30% ongoing maintenance

---

## 🚦 Risk Assessment & Mitigation

### High Risk Items
1. **Model Training Failure**: Mitigation - Start with smaller datasets, use proven techniques
2. **Voice Quality Degradation**: Mitigation - Extensive A/B testing, fallback to Google TTS
3. **Performance Issues**: Mitigation - Comprehensive load testing, optimization pipeline
4. **Halloween Party Failure**: Mitigation - Backup system, real-time monitoring

### Medium Risk Items
1. **Integration Complexity**: Mitigation - Incremental approach, comprehensive testing
2. **Cost Overruns**: Mitigation - Usage monitoring, automatic cutoffs
3. **Model Bias/Inappropriate Responses**: Mitigation - Content filtering, response validation

### Low Risk Items
1. **Configuration Management**: Well-understood problem space
2. **Backward Compatibility**: Existing interface contracts are stable
3. **Documentation**: Incremental documentation approach

---

## 📚 Resources & References

### Technical Documentation
- [OpenAI TTS API Documentation](https://platform.openai.com/docs/guides/text-to-speech)
- [Hugging Face Fine-tuning Guide](https://huggingface.co/docs/transformers/training)
- [Ollama Local Deployment](https://ollama.ai/docs)
- [LoRA Fine-tuning Tutorial](https://huggingface.co/docs/peft/conceptual_guides/lora)

### GANGLIA Codebase
- Current TTS implementation: `tts.py`
- Conversation handling: `conversational_interface.py`
- Configuration management: `config/ganglia_config.json`
- Quest system: `hotwords.py` + config hotwords section

### Training Resources
- Google Colab free tier: 15GB VRAM, sufficient for 7B model LoRA training
- Hugging Face model hub: Base models and training utilities
- Audio processing libraries: SoX, pydub for voice effects

---

## 📝 Decision Log

### Key Decisions Made
1. **Two-Phase Approach**: TTS modernization separate from model training
2. **Hybrid Architecture**: Local model + OpenAI fallback for optimal cost/performance
3. **Backward Compatibility**: Maintain all existing interfaces during transition
4. **Voice Selection**: Onyx as primary choice with audio post-processing
5. **Training Platform**: Google Colab free tier for cost optimization

### Decisions Pending
- [ ] Final voice selection after testing
- [ ] Training dataset size and composition
- [ ] Fallback thresholds for hybrid routing
- [ ] Production monitoring and alerting strategy

---

## 🎯 Next Steps

### Immediate Actions (This Week)
1. **Voice Testing**: Test OpenAI TTS voices for GANGLIA character fit
2. **Data Extraction**: Begin extracting training data from current system
3. **Environment Setup**: Prepare Google Colab training environment
4. **Architecture Review**: Validate technical approach with stakeholders

### Sprint Planning
- **Sprint 1**: OpenAI TTS MVP implementation
- **Sprint 2**: Custom model training and local deployment
- **Sprint 3**: Hybrid system integration and testing
- **Sprint 4**: Enterprise hardening and production readiness

---

*Last Updated: December 2024*
*Document Owner: GANGLIA Development Team*
*Status: Planning Phase - Ready for Implementation*
