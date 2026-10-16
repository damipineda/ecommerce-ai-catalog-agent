# E-Commerce Catalog & Customer Support AI Agent

Turn messy Spanish product notes into a validated catalog draft, SEO metadata and a customer support answer using **Ollama Cloud** and Python.

Bring your own API key. No local Ollama installation, model download or GPU is required.

## What it does

- Accepts product notes and a customer question from a JSON file.
- Grounds the prompt in editable shipping and warranty policies.
- Validates required fields, SEO length limits and JSON types with Pydantic.
- Requires feature bullets to be literal extracts from the original notes.
- Makes one repair request if model output fails validation.
- Exports a draft with its model, mode, policies and an explicit human-review flag.
- Includes an offline demo and automated tests that need no API credentials.

This is a single-request AI workflow with bounded validation recovery, not an autonomous tool-using agent or a retrieval system. Store rules are supplied directly in the prompt; no vector database or RAG retrieval is implemented.

## Quickstart

Requires Python 3.11 or later.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

Try the deterministic preview without an account or a network request:

```bash
python agent.py --demo
python agent.py --demo --input examples/backpack.json
```

The demo copies input text and labels its support response as a preview. It does **not** run an AI model.

## Use real AI through Ollama Cloud

1. Create your own key at [Ollama API keys](https://ollama.com/settings/keys).
2. Copy `.env.example` to `.env` and fill in `OLLAMA_API_KEY` privately.
3. Set `OLLAMA_MODEL` to a model from the [cloud catalog](https://ollama.com/search?c=cloud). The example uses `gemma4:31b`; model availability can change. Use the API model name rather than the local CLI `:cloud` alias.
4. Edit `business_rules.json` to match your store. Included policies are fictional examples, not delivery promises. Set unknown policies to `null`.
5. Run:

```bash
python agent.py
python agent.py --input examples/backpack.json --output backpack-draft.json
```

The output file must not already exist. CLI paths are relative to your current directory; default examples and `.env` resolve beside `agent.py`. Shell environment variables take precedence over `.env`.

Ollama Cloud requires an account and has usage limits; this project does not promise unlimited free inference. Check the provider's [plans](https://ollama.com/pricing) and [cloud documentation](https://docs.ollama.com/cloud). Your input and business rules are sent to the hosted provider in AI mode. Never commit `.env` or API keys.

## Architecture

```text
Product notes + customer question + store policies
                   |
           Input validation (Pydantic)
                   |
         Ollama Cloud POST /api/chat
                   |
     JSON + length + literal feature validation
                   |
       One repair attempt if needed
                   |
      JSON draft for human review
```

Ollama Cloud [does not currently support schema-constrained structured outputs](https://docs.ollama.com/capabilities/structured-outputs). The schema is included in the prompt and validated locally. Invalid final output causes a nonzero exit; API failures never silently become demo results. The client calls the hosted HTTPS endpoint directly using Python's standard library.

## Input and output

See [thermos input](examples/thermos.json) and [missing-specification example](examples/backpack.json). The latter asks about waterproofing and laptop fit without supplying those facts: the model is instructed to acknowledge uncertainty.

Each result contains:

| Field | Purpose |
| --- | --- |
| `mode`, `model` | Distinguish a demo from cloud inference |
| `sku_id` | Stable draft ID derived from notes; not a merchant-assigned SKU |
| `listing.standardized_title`, `short_pitch` | Suggested product copy |
| `listing.bullet_features` | Exact extracts checked against input |
| `listing.category_path` | Suggested category, not a platform taxonomy |
| `listing.seo_metadata` | Title up to 60 characters, description up to 155, 1–5 keywords |
| `listing.customer_faq_response` | Answer grounded by product notes and policies |
| `listing.missing_information` | Questions to resolve before publishing |
| `review_required`, `store_policies` | Review status and policy provenance |

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests use mocked cloud responses and cover schema limits, unsupported feature rejection, missing keys, repair behavior, authentication headers and provider errors. All 12 tests passed locally on Python 3.13. A [GitHub Actions template](docs/github-actions-tests.yml.example) covers Python 3.11–3.13; CI is not yet enabled because the publishing credential lacks the `workflow` permission. To enable it, copy the template to `.github/workflows/tests.yml` using an account or token with that permission. Local tests do not establish live model quality or cloud account access.

## Verified cloud example

On October 15, 2026, the project owner ran `python agent.py` with their own Ollama Cloud key and `gemma4:31b`. The terminal output showed a successful `ollama_cloud` result for [the thermos input](examples/thermos.json), including validated product copy, SEO metadata and a customer answer distinguishing dispatch time from delivery time.

The [saved cloud output](examples/cloud-output.json) reproduces that user-provided terminal result. It contains no API credentials. The [demo output](examples/demo-output.json) is separately labeled and does not represent model inference. This records one successful example, not a general model-quality evaluation. Human review remains required, and the shipping and warranty policies are still fictional examples.

## Scope and limitations

- Schema validation checks structure, not truth. Literal feature checks reduce unsupported claims in bullets; generated titles, SEO and support prose still need human review.
- Prompt instructions are not a security boundary against prompt injection.
- No Shopify/Meta import contract, catalog publication, persistent customer history or storefront integration is implemented.
- One live cloud example is documented above. Other products, models and account limits require separate verification with the user's own key.

## Descripción para portafolio

“Flujo en Python que convierte notas de productos en fichas de catálogo y respuestas de soporte, con Ollama Cloud, validación Pydantic y pruebas automatizadas”. Antes de presentarlo en una hackatón, revisa las reglas del evento sobre proyectos previos.
