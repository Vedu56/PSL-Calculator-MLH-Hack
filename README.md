# PSL Calculator 🗿

An experimental AI facial-aesthetics app developed for **QM Hacktoberfest Hack Day**, Queen Mary University of London, on **24 October 2026**.

Upload a selfie, request a rating out of 10, and receive a short appearance-related explanation through a Streamlit interface.

> Hackathon prototype in active development. The interface and API request code are implemented; successful live model inference still needs verification.

## About the Project

PSL Calculator explores image-based AI interaction through a face-rating experience inspired by looksmaxing communities.

The project has two intended modes:

- **Solo Analysis:** upload a photograph and request an individual score and feedback.
- **Face-Off PvP:** compete in a multiplayer comparison across timed rounds.

Solo Analysis is the current prototype. PvP is planned and is not included in the current application code.

Scores are generated responses, not scientifically validated measurements of attractiveness.

## Current Features

- Upload JPG, JPEG or PNG images.
- Preview the uploaded photograph.
- Start an analysis using the **Calculate PSL Score** button.
- Send the image and a text prompt to a configured Hugging Face endpoint.
- Request a JSON response containing a score and short advice.
- Display the returned score out of 10.
- Display advice beneath the score.
- Show a loading indicator during the request.
- Use a black-and-white interface with custom CSS and Audiowide typography.
- Load the Hugging Face token from an environment variable.

## How It Works

1. The user uploads an image through Streamlit.
2. The application displays a preview.
3. Clicking **Calculate PSL Score** encodes the image as Base64.
4. The Python application sends the image and prompt through an HTTP POST request.
5. The code attempts to extract generated text from the response.
6. It removes surrounding Markdown code fences when present and parses the text as JSON.
7. Streamlit displays the score and advice.

The prompt requests this response structure:

```json
{
  "psl_score": 7.0,
  "advice": "A short explanation or appearance-related suggestion."
}
```

This example illustrates the requested format, not an actual analysis result.

## Rating System

The prompt asks the model for a score from **1 to 10**.

The current implementation does not calculate facial landmarks, symmetry, distances or weighted proportions. It requests a rating directly from the vision-language model.

There is currently no validated scoring formula, population benchmark or guarantee that repeated analyses will produce consistent results.

The parser also does not yet enforce the score range or validate every response field.

## Technology Stack

| Technology | Purpose |
| --- | --- |
| Python | Application logic |
| Streamlit | Web interface, uploads and result display |
| Requests | HTTP requests to the model endpoint |
| python-dotenv | Loading local environment variables |
| Base64 | Encoding image bytes for the request |
| JSON | Parsing structured output |
| HTML and CSS | Interface styling |
| Google Fonts | Audiowide typography |
| Hugging Face | Configured external inference service |
| Google PaliGemma | Intended image-and-text model |

### Configured Model

Model identifier:

```text
google/paligemma-3b-mix-224
```

Endpoint currently used in the code:

```text
https://api-inference.huggingface.co/models/google/paligemma-3b-mix-224
```

Endpoint availability, task support and request-format compatibility must be verified. Having a model identifier and token does not by itself confirm that hosted inference is available.

- [PaliGemma model card](https://huggingface.co/google/paligemma-3b-mix-224)
- [Gemma model terms](https://ai.google.dev/gemma/terms)

This prototype targets PaliGemma 3B. It does not currently integrate Gemma 4 or the Gemini API.

## Run Locally

The instructions below assume the supplied application code is saved as `score_face.py`. Substitute the actual filename if different.

### Open the project directory

Download or clone the repository, then open a terminal in its root folder.

### Create a virtual environment

```bash
python3 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install streamlit requests python-dotenv
```

### 4. Configure the token

Use an account and token with the permissions required by the chosen inference service. Complete any model-access requirements shown on the model page.

### Start the application

```bash
python -m streamlit run score_face.py
```

Open the local URL printed in the terminal.

Starting the interface does not confirm that the external inference request is working.

## Current Fallback Behaviour

The current code catches exceptions during the API request and response parsing, then substitutes:


- A fixed advice message that does not depend on the uploaded image.

The exception is printed to the server console, but the interface currently displays the fallback in the same way as a model response.

**Fallback output is placeholder data, not AI analysis.** It must not be presented as evidence of successful inference during a demonstration.

A priority improvement is to show a clear error with a retry option, or explicitly label a separate demonstration mode.

## Planned Features

### Improved Solo Analysis

- Dedicated home screen and mode selection.
- Separate sections for highlighted features and suggestions.
- Clearer explanations of generated ratings.
- Image suitability checks.
- Validated response fields and score ranges.
- Visible API error messages and retry controls.

### Face-Off PvP

A planned two-player mode featuring:

- Player nicknames and separate image uploads.
- Three rounds.
- A proposed 15-second timer per round.
- Side-by-side results.
- Round points and an overall match result.
- A tiebreaker when needed.
- A rematch option.

The round-winning rule and timer behaviour are still being finalised. PvP scoring should use the same criteria for both players and exclude fallback results.

## Limitations

- The model has not been validated as an attractiveness assessor.
- Scores and explanations may be inconsistent or inaccurate.
- Lighting, pose, expression and image quality may affect responses.
- Asking a model to be objective does not make its ratings objective.
- Generated advice may contain unsupported claims about facial anatomy or appearance.
- The current code does not check for exactly one face.
- HTTP status handling and response validation need improvement.
- A successful-looking result may currently be fixed fallback data.

This is an entertainment and learning prototype. Its output is not a medical assessment or a measure of personal worth.

## Image Handling

Uploaded images are received by the Streamlit server. When analysis is requested, image data is included in an outbound request to the configured Hugging Face endpoint.

Base64 is an encoding format, not encryption.

The supplied code does not explicitly save uploaded images to disk or a database. This does not establish the retention behaviour of the hosting environment or external service.

Only upload images you own or have permission to use. Keep API credentials private.

## Team

Built by a team of three at QM Hacktoberfest.

- **Annukul Ghale  / Annukul06** — Frontend, ideas
- **Vedant Trivedi / Vedu56** — Backend, planning - initial idea, APIs, tokens and app deployment.
- **Mustafe Musse / africandude** — Frontend, prompting 

## Demo

**Unlisted YouTube video:** https://youtube.com/shorts/MkwQNWr8UYE?si=22yp6nTkJ7X-nx4R , https://youtube.com/shorts/51Be39lfAwY?si=w9_CuQH6PsaJ7y1t , https://youtube.com/shorts/1bp-vodpuLs?si=3L2aHVwLp03RagxT

**Live application:**  https://psl-calculator-mlh-hack-5dnqeov6yyaqpqkqq9eezj.streamlit.app/

The submission video should demonstrate the working application and clearly distinguish live model output from any demonstration data.


The current Gemma 4 integration does not establish eligibility for the **Best Use of Gemma 4** prize, which requires an actual Gemma 4 integration.

[Event and submission page](https://www.mlh.com/events/hacktoberfest-hack-day-london-x-queen-mary-computer-science-society)

## Licence

See the LICENSE for the project's source-code licence.

Third-party packages and model weights retain their own licences and terms. The repository's licence does not replace the PaliGemma model terms.

## Acknowledgements

- Queen Mary Computer Science Society and Major League Hacking.
- Google for PaliGemma.
- Hugging Face for model distribution and inference tooling.
- Streamlit and the developers of the project's dependencies.
