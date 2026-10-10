# Mobile case recording

## Requirements

### Traceable source replay
Recordings MUST identify the frozen source and any date transform. Each model call MUST receive only the source prefix available at its recorded revision, without future labels. Synthetic readbacks MUST remain explicitly simulated.

### Separate scripted and live modes
A scripted recording MUST report zero model calls. A live recording MUST preserve actual provider receipts, requested/observed model IDs, and frozen inputs. An edited video MUST NOT imply model agreement with an operator override or claim physical delivery from a local booking receipt.

### Bounded recording and delivery
The case-001 recorder MUST create a fresh local case and cap live model submissions at five, without automatic retry of failed or uncertain calls. Raw captures and edit manifests MUST remain available. Final mobile exports MUST contain five ten-second stages at 1080×1920 and 30 fps. Existing final files MUST NOT be overwritten.

### Verification boundary
Transport success, correct local state transitions and sampled-frame media QA MUST be reported separately from model semantic quality and user aesthetic approval. Additional final-state captures MUST be read-only and disclosed.
