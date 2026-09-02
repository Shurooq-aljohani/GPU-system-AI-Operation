# The locked model
* Model id: Qwen/Qwen2.5-1.5B-Instruct-AWQ
* Quantisation: awq
* Why this one: passed smoke, VRAM headroom, quality held

# The launch flags
--model Qwen/Qwen2.5-1.5B-Instruct-AWQ --dtype half --max-model-len 4096 \
--gpu-memory-utilization 0.85 \
--quantization awq \
--enable-auto-tool-choice --tool-call-parser hermes
* Tool-call parser: hermes

# The smoke score
* Score (valid behaviours out of 10): 10
* Distractor stayed call-free in the majority: yes
* Passed the gate (>= 8/10 and distractor majority clean): yes
* Measured against: AWQ

# Quality spot check note
* The quantized build held up exceptionally well across all prompts with no noticeable degradation compared to fp16.
