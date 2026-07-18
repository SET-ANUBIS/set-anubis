# R1 — Core model interface

**Question.** Can the release load the bundled HNL UFO, expose its model content,
and update an LLP mass through the public API?

- `input/config.json`: model name, PDG identifiers and parameter update.
- `run.py`: executes the model-interface check.
- `output/summary.json`: generated result; ignored by Git.
- `expected_output/summary.json`: version-controlled reference result.
