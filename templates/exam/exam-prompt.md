# CSE 463 — Per-Student Computer Vision Exam Generation Prompt

You are generating a **personalized oral/written exam** for ONE student, based on the
Computer Vision homework they submitted. **The entire point of this exam is to test
whether the student actually understands the work they handed in** — many students used
LLMs to produce the report and code, so the questions must be impossible to answer well
without having genuinely understood their own submission.

## Inputs

You are given the student's `_exam_input.md` bundle, which contains:
- Their **report** text (methodology, results, discussion)
- Their **code** (`.py` / `.ipynb` cells, with outputs)
- Sampled **result images** (downscaled thumbnails — Read the listed paths if you need
  to see what their output actually looks like)
- A list of large data/model files (names only)

**Read the bundle carefully.** If thumbnails are listed, Read at least the most
informative ones (e.g. a segmentation/detection result) before writing questions —
your questions should reference what their results actually show.

## Output

Write `exam.json` matching `templates/exam/exam-schema.json`:
- **EXACTLY 4 questions**, **25 pts each**, **100 pts total**, **90 minutes**.
- **2 questions `submission-specific`** (about their own report/code/results)
- **2 questions `general-cv`** (standard CV concepts that their homework touches)
- Each question MUST have `expected_answer` + a `rubric` whose point values sum to 25.

Each question must be answerable in ~20 minutes of writing on a lined sheet.

## The two `submission-specific` questions — this is where you catch LLM-only work

Make these concrete and tied to THEIR specific choices. Good patterns:

- **"Why did you do X and not Y?"** — Point at a specific decision in their code/report
  (a kernel size, a threshold, a color space, a specific layer, a data-augmentation
  choice, a loss function) and ask them to justify it and name the alternative.
- **"Trace / predict"** — Give a small concrete input and ask what their pipeline would
  output, and why. (e.g. "Your Canny uses low=50, high=150. For a faint edge with
  gradient magnitude 80, walk through what happens.")
- **"Explain this excerpt"** — Paste a ~10-line `code_excerpt` from THEIR submission and
  ask what it computes and why it's there. Reward understanding, not paraphrase.
- **"Failure analysis"** — Point at a result image and ask where their method fails and
  why (referencing the actual artifact you can see in the thumbnail).
- **"Inconsistency probe"** — If the report claims something the code doesn't do (or vice
  versa), ask a question that only someone who understands both can resolve.
- **Pair work:** if `is_pair`, ask about the part *this* student claims they did.

❌ Avoid generic questions that an LLM answers from the textbook alone
   ("What is convolution?"). 
✓ Every submission-specific question must cite the student's own name for a variable,
   function, parameter value, dataset, or a visible feature of their result image.

## The two `general-cv` questions

Pick standard CV concepts **that the student's homework actually exercises**, so the two
halves connect. Choose from the topic the homework is about, e.g.:

- Image formation, color spaces, sampling/aliasing
- Linear filtering & **convolution** (separability, boundary handling, kernel design)
- Gradients & **edge detection** (Sobel, **Canny** non-max suppression + hysteresis)
- **Feature detection/matching** (Harris corners, SIFT/ORB, descriptor matching, RANSAC)
- Geometric transforms, **homography**, image warping/stitching
- **Segmentation** (thresholding, k-means, watershed, graph-based), morphology
- Camera models, **stereo / epipolar geometry**, disparity
- Optical flow & motion
- **Deep learning for vision** (CNN building blocks, receptive field, pooling, the
  classification/detection/segmentation head, **IoU / mAP / precision-recall**, overfitting)

These can be slightly more open ("Explain why X works / when it fails"), but still keep
them grounded in the method the student used.

## Quality self-check (do this before finalizing)

- [ ] Exactly 4 questions, 25 pts each, rubric sums to 25 each.
- [ ] 2 submission-specific reference the student's OWN parameters/code/results by name.
- [ ] 2 general-cv are about concepts the homework actually uses.
- [ ] At least one question includes a `code_excerpt` from their submission OR references a
      specific result image.
- [ ] No question is answerable by copy-pasting a definition; each needs *their* context.
- [ ] `expected_answer` is specific enough that a TA/AI can grade fairly.
- [ ] Questions are in English; TA-facing notes/comments may be Turkish.

## Reference example structure (not content — adapt to the actual submission)

```json
{
  "student_id": "220104004061",
  "student_name": "AHMET YILMAZ",
  "homework": 1,
  "homework_title": "Edge detection & feature matching",
  "duration_minutes": 90,
  "total_points": 100,
  "is_pair": false,
  "pair_partners": [],
  "questions": [
    {
      "number": 1, "title": "Your Canny thresholds", "points": 25,
      "category": "submission-specific", "reference": "Edge detection / Canny",
      "text": "In edges.py you call cv2.Canny(img, 50, 150)...",
      "code_excerpt": "edges = cv2.Canny(blur, 50, 150)\n...",
      "expected_answer": "The two thresholds drive hysteresis...",
      "rubric": ["Explains low/high hysteresis role (10)", "Justifies their 50/150 vs image contrast (8)", "States effect of raising/lowering (7)"]
    }
  ]
}
```

After writing `exam.json`, render it:
```
python tools/render_exam_pdf.py --exam <path>/exam.json
```
This produces `exam.pdf` (student copy) and `key.md` (TA/AI grading key).
