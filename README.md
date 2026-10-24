# PSL Calculator

An experimental facial-analysis and face-rating project developed by a team of three for **QM Hacktoberfest Hack Day**, Queen Mary University of London, on **24 October 2026**.

## Overview

PSL Calculator explores how computer vision and facial geometry can be used to create an interactive, explainable face-analysis experience.

Inspired by looksmaxing and online face-rating tools, our aim is to let users upload a photograph, explore selected facial measurements, and understand how those measurements contribute to a PSL-style score.

The emphasis is on making the calculation visible: showing what is measured, how it is calculated, and what its limitations are.

> This project is under active development. Features and integrations listed as planned may change during the hackathon.

## Planned Features

- **Photo upload:** analyse a clear, front-facing photograph.
- **Facial landmark detection:** identify points around the eyes, nose, mouth and facial outline.
- **Visual overlay:** display the landmarks and measurement lines on the photograph.
- **Facial proportions:** calculate selected distance ratios, including relative eye spacing and face width-to-height ratio.
- **Symmetry estimates:** compare selected corresponding landmarks.
- **Explained scoring:** show how individual measurements contribute to an experimental PSL-style rating.
- **AI explanations:** provide a readable explanation of the measurements and their limitations.
- **Input validation:** provide feedback when a photograph is unsuitable for analysis.

### Stretch Goal

Compare two photographs of the same person to demonstrate how pose and expression affect the measurements.

## How It Is Intended to Work

1. The user uploads a photograph.
2. A computer-vision model identifies facial landmarks.
3. Application code calculates distances, ratios and symmetry measurements.
4. A documented scoring formula combines selected measurements.
5. The interface displays the measurements, visual overlay and score breakdown.
6. An optional AI integration explains the results in plain language.

Numerical measurements should come from the calculation code. The language model's role is to explain those results, rather than invent measurements.

## Technology

The final stack is being confirmed during development.

| Component | Current or proposed technology |
| --- | --- |
| Source code and collaboration | GitHub |
| Existing Python file | `score_face.py` |
| Facial landmark detection | MediaPipe Face Landmarker — proposed |
| Web interface | Framework to be confirmed |
| AI explanations | Gemma 4 through the Gemini API — proposed |
| Measurement logic | Team-written geometry and scoring calculations |

### Proposed AI Integration

We plan to explore Gemma 4 for explaining calculated measurements and answering questions about the results.

The intended contribution is to make the numerical analysis understandable, including explaining why photographs of the same person may produce different measurements.

The exact model, configuration and dependencies will be documented once integration is complete.

References:

- [MediaPipe Face Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker)
- [Gemma through the Gemini API](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api)
- [Gemma Terms](https://ai.google.dev/gemma/terms)

## Project Files

- `score_face.py` — Python source file; implementation details will be documented as development progresses.
- `README.md` — project overview and documentation.
- `LICENSE` — repository licence terms.
- `.gitignore` — files excluded from version control.

## Getting Started

Installation and execution instructions will be added once the dependencies and application entry point are finalised.

The completed instructions will cover:

1. Required runtime and version.
2. Dependency installation.
3. Model downloads, if required.
4. Environment variables for any external API.
5. Commands to run the application.

Do not commit API keys or other credentials to the repository.

## Understanding the Results

The PSL-style rating is an experimental entertainment score based on a team-defined formula. It is not a scientifically validated measure of attractiveness, health or personal worth.

Results may be affected by:

- Head position and camera angle.
- Camera distance and perspective.
- Lighting and image quality.
- Facial expression.
- Glasses, hair or other obstructions.
- Errors in landmark detection.

Facial proportions are not universal beauty standards. Measurements from a photograph should not be treated as precise physical measurements.

The final scoring documentation will identify the measurements, normalisation methods and component weights used.

## Privacy

Our intended approach is to minimise the collection and retention of photographs.

Browser-based image processing and sending only calculated measurements for AI explanations are proposed design choices. Actual processing, external requests and retention behaviour will be documented once implemented.

Only upload photographs you own or have permission to use.

## Team

A team of three participating in QM Hacktoberfest.

- **[Vedant]** — [Contribution]
- **[Annukul]** — [Contribution]
- **[Mustafe]** — [Contribution]

## Demo

**Video:** [Add unlisted YouTube link]

**Live application:** [Add deployment link, if available]

The hackathon demo will show the working application, explain the team's contribution, and describe how any AI models are used.

## Hackathon

**Event:** Hacktoberfest Hack Day — Queen Mary Computer Science Society  
**Date:** 24 October 2026  
**Submission deadline:** 15:30, London time

Potential prize categories, subject to the completed implementation meeting the requirements:

- Best Overall Hack.
- Best Open-Source AI Project.
- Best Use of Gemma 4.

[Event and submission page](https://www.mlh.com/events/hacktoberfest-hack-day-london-x-queen-mary-computer-science-society)

## Licence

See [LICENSE](LICENSE) for this repository's licence terms.

Third-party libraries and model weights remain subject to their own licences and terms. The final dependency list will identify the packages, models and versions used.

## Before Submission

- [ ] Update this README to reflect the implemented features and final technology stack.
- [ ] Add installation and run instructions.
- [ ] Document the scoring formula.
- [ ] Add team names and actual contributions.
- [ ] Confirm the repository is public and has an appropriate open-source licence for the open-source AI prize.
- [ ] Document model and dependency licences.
- [ ] Add an unlisted YouTube demo of no more than three minutes.
- [ ] Demonstrate the working project and relevant AI code.
- [ ] Submit before 15:30 and select every eligible prize category.

## Acknowledgements

Thanks to Queen Mary Computer Science Society and Major League Hacking for organising the event, and to the developers of the open-source tools used in the project.
