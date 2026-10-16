# Chapter labs and actual model evidence

From the source checkout, `py -3.11 examples/chapter_lab.py --all` runs eighteen isolated, disposable checkpoints. Each reports its exact scope and explicitly states that no model was called. `py -3.11 -m unittest discover -s tests -v` runs the broader automated suite, including controlled model doubles. Neither command establishes generated-answer quality.

## Collect actual local answers

Configure a downloaded local model as described in [setup](setup.md), then run:

```powershell
py -3.11 examples/evaluate_local.py --output data/local-evaluation.json
```

The collector creates synthetic records, asks paired with-memory/without-memory questions, and retains the actual requests and replies. Existing evidence files are not overwritten. Hint matches are aids for review, never an accuracy score. Assess support, citation IDs, state preservation, current instructions, scope, and uncertainty against the supplied records.

## Optional CPU-only experiment

`examples/evaluate_cpu.py` uses the pinned Qwen3-0.6B revision named in its source. It is separate from the standard-library application and needs compatible `torch`, `transformers`, and `huggingface_hub` installations. Its help explains explicit download consent, local model directory, and new output filename. After the optional download it loads local files only, disables remote code, uses CPU computation, and records the model revision and weight hashes. Model licenses remain separate.

The recorded development probe used torch 2.12.0.dev20260329+cu128 and transformers 4.51.0 on Windows, with CPU execution and greedy non-thinking decoding. It exposed unsupported completion claims and a fabricated citation placeholder. This is evidence about that small experiment, not a model ranking or recommended decoding benchmark. A model fitting in memory does not establish answer reliability.

## Optional read-only local agent

```powershell
py -3.11 examples/memory_agent.py --help
```

The example creates its own synthetic store and uses a compatible local tool-calling engine. Its sole tool recalls records within the application-selected project. Turn and call limits prevent an unbounded loop. Unknown tools, extra scope arguments, and malformed calls are rejected. It returns a trace and compares the store before and after; no shell or write tools exist.

Actual development runs used two model turns and one scoped recall. One answer overstated an unverified restore, and a subsequent run still used a misleading success heading despite preserving uncertainty in the body. The failures remain part of the book's evidence. A valid tool call or citation ID is not proof that an answer correctly interpreted the record.

Keep evaluation outputs private unless checked for distribution. The examples use fictional data; running them against private data would change that boundary. No model weights, raw databases, exports, or backups belong in Git.
