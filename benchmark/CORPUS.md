# Benchmark Corpus

Five repos selected for benchmarking noxaudit across providers, models, and focus areas.
Each repo is pinned at a specific commit SHA for reproducibility.

## Corpus

| Repo | Language | Size | Commit SHA | Role |
|------|----------|------|------------|------|
| `atriumn/noxaudit` | Python | ~526 KB | `1503cbf22b08bbe7e64962221c7075474ed33f57` | Medium Python — our own product (dogfood) |
| `atriumn/tokencost-dev` | TypeScript | ~3.9 MB | `7ee1423562cdc6dbecfd4959da789fc11da4a3b1` | Medium TS — MCP server, real-world complexity |
| `atriumn/cryyer` | TypeScript | ~1 MB | `4f7ec8270bb9957e4276c063ca421a560daafd67` | Small TS — LLM-powered, Atriumn product |
| `tiangolo/fastapi` | Python | Large (400+ files) | `ca5f60ee72f35fb2134d8b5d26bbb75965bcff66` | Large Python — stress-test context windows |
| `theskumar/python-dotenv` | Python | Small (~10 files) | `da0c82054f1ec1e03d57356d49b0b9ad09eb4209` | Small Python — hallucination canary |

## Rationale

### atriumn/noxaudit
Dogfooding: we run noxaudit against itself. Medium-sized Python repo (~526 KB) with a real
security surface (API keys, provider auth, config loading). Known codebase gives us a ground
truth to evaluate finding quality. Any model that misses obvious issues in our own code is
disqualified for production use.

### atriumn/tokencost-dev
Medium TypeScript MCP server (~3.9 MB). Represents the TypeScript ecosystem and an MCP-pattern
codebase. Large enough to stress model context handling, small enough to stay under most
provider limits without pre-pass.

### atriumn/cryyer
Small TypeScript LLM-powered product (~1 MB). Tests how models handle a modern TS codebase
with AI integrations — prompt injection, API key handling, output parsing. Provides a
TypeScript counterpart to python-dotenv for cross-language comparison at small scale.

### tiangolo/fastapi
The de facto standard Python web framework — 400+ files, battle-tested, real security
surface (auth middleware, dependency injection, input validation, OpenAPI generation).
Serves two purposes:
1. **Context stress test**: forces models to handle large repos gracefully
2. **Security surface**: auth flows, header parsing, and middleware offer genuine
   findings without being a deliberately broken codebase

### theskumar/python-dotenv
Deliberately simple (~10 files), well-maintained, no known security issues.
Acts as a **hallucination canary**: models that find many high-severity issues in
python-dotenv are likely hallucinating. Expected finding count: 0–2 low-severity
observations at most. Models producing many findings here score poorly on precision.

## Coverage Matrix

| Dimension | Values |
|-----------|--------|
| Languages | Python, TypeScript |
| Sizes | Small (python-dotenv, cryyer), Medium (noxaudit, tokencost-dev), Large (fastapi) |
| Quality | Clean/well-maintained (python-dotenv, fastapi), Active product (noxaudit, cryyer, tokencost-dev) |
| Ownership | Atriumn (noxaudit, tokencost-dev, cryyer), Open source (fastapi, python-dotenv) |

## Setup

Clone each repo and check out the pinned commit before running benchmarks:

```bash
# Clone to a local directory (adjust paths as needed)
mkdir -p ~/benchmark-repos

git clone https://github.com/atriumn/noxaudit ~/benchmark-repos/noxaudit
git -C ~/benchmark-repos/noxaudit checkout 1503cbf22b08bbe7e64962221c7075474ed33f57

git clone https://github.com/atriumn/tokencost-dev ~/benchmark-repos/tokencost-dev
git -C ~/benchmark-repos/tokencost-dev checkout 7ee1423562cdc6dbecfd4959da789fc11da4a3b1

git clone https://github.com/atriumn/cryyer ~/benchmark-repos/cryyer
git -C ~/benchmark-repos/cryyer checkout 4f7ec8270bb9957e4276c063ca421a560daafd67

git clone https://github.com/tiangolo/fastapi ~/benchmark-repos/fastapi
git -C ~/benchmark-repos/fastapi checkout ca5f60ee72f35fb2134d8b5d26bbb75965bcff66

git clone https://github.com/theskumar/python-dotenv ~/benchmark-repos/python-dotenv
git -C ~/benchmark-repos/python-dotenv checkout da0c82054f1ec1e03d57356d49b0b9ad09eb4209
```

Then update the `path:` entries in `benchmark/corpus.yml` to match your local paths,
and run:

```bash
python scripts/benchmark.py matrix benchmark/corpus.yml
```

## Updating the Corpus

To re-pin the corpus to newer commits:

```bash
# For each repo, get the latest commit SHA:
git -C ~/benchmark-repos/fastapi pull && git -C ~/benchmark-repos/fastapi rev-parse HEAD

# Update the SHA in this file and in benchmark/corpus.yml
```

All benchmark results in `benchmark/results/` are keyed to these commit SHAs via the
`meta.repo_commit` field, making it safe to re-run after updates without confusing old
and new results.
