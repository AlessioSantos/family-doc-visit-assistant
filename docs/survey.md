# Survey-based validation (Poland): why this project exists

This MVP was shaped by a short questionnaire study with practicing physicians in Poland.  
The goal was to validate whether documentation workload and “free-text noise” are meaningful daily pain points, and to translate those findings into concrete product requirements.

> **Privacy note:** The survey was collected anonymously. No patient data was used. No personal identifiers of respondents are stored in this repository.

---

## Context

Family medicine often involves:
- repeated, time-consuming documentation,
- bureaucracy that competes with patient-facing time,
- intake narratives that are long, unstructured, and hard to reuse in clinical notes.

The survey was designed to check whether these issues are experienced in real practice and what an assistant would need to do to be useful (without giving medical advice).

---

## Method (high level)

- **Population:** practicing physicians (family medicine / primary care) in Poland  
- **Instrument:** short questionnaire (mix of multiple-choice + free-text)  
- **Period:** _(fill if you want)_  
- **Sample size:** _(fill if you want; optional)_  
- **Collection:** anonymous, voluntary participation  
- **Data handling:** responses summarized qualitatively; no identifiers stored

---

## What we asked (question themes)

The questionnaire focused on:

1) **Documentation burden**
- How much time goes to documentation vs patient interaction?
- Which parts of documentation feel most repetitive?

2) **Pain points in patient narratives**
- Do patients provide long, non-specific stories?
- What information is most often missing for a usable note?

3) **What would actually help**
- Would structured pre-visit intake reduce note-writing time?
- Which structured elements are the most useful?
  - timeline by dates
  - symptom severity / change
  - temperature history (graph)
  - attachments (e.g., cough audio, rash photo)

4) **Safety expectations**
- What must the tool *not* do?
- How should uncertainty / missing data be handled?

---

## Key findings (qualitative summary)

Across responses, the most consistent themes were:

- **Routine documentation is a real, daily burden.**  
  Respondents described paperwork and repetitive note-writing as a major time sink.

- **Unstructured narratives reduce efficiency.**  
  “Free-text noise” (too much irrelevant detail, unclear timeline, missing measurements) makes documentation slower and less reliable.

- **Structured pre-visit data is seen as helpful.**  
  Respondents highlighted the value of a date-based timeline and structured measurements (especially temperature patterns).

- **Safety constraints are essential.**  
  The tool should not provide diagnosis or treatment recommendations; it should output a draft that can be reviewed and edited.

---

## How the survey shaped this MVP (requirements → features)

**Survey requirement:** reduce “free-text noise” and missing details  
**Implemented:** structured intake JSON + follow-up questions list for missing fields

**Survey requirement:** make timeline explicit  
**Implemented:** timeline-by-dates (events with change/severity)

**Survey requirement:** keep measurements readable  
**Implemented:** temperature graph entries (time-of-day + value)

**Survey requirement:** allow attachments without interpretation  
**Implemented:** optional rash photo / cough audio support (referenced factually)

**Survey requirement:** strict safety boundaries  
**Implemented:** system-level rules: no diagnosis, no treatment, no dosing; unknowns are marked and questioned

---

## Limitations

- Questionnaire-based validation is qualitative and context-dependent.
- Findings describe perceived workflow pain points rather than clinical outcomes.
- This MVP is a documentation assistant; clinician review is always required.

---

## Reproducible demo

To reproduce the end-to-end demo on synthetic cases:

```powershell
python scripts/run_demo.py