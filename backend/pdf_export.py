import os
import re
from datetime import date

from fpdf import FPDF, XPos, YPos

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

FONT_DIR = "/System/Library/Fonts/Supplemental"
FONT_FILES = {
    "": os.path.join(FONT_DIR, "Arial.ttf"),
    "B": os.path.join(FONT_DIR, "Arial Bold.ttf"),
    "I": os.path.join(FONT_DIR, "Arial Italic.ttf"),
    "BI": os.path.join(FONT_DIR, "Arial Bold Italic.ttf"),
}

BLACK = (0, 0, 0)

# Font sizes: LaTeX article class at 10pt base. \Large = 14.4pt, \small = 9pt,
# everything else (section headers, job headers, bullets, skills) is \normalsize = 10pt.
SIZE_NAME = 14.4
SIZE_CONTACT = 9
SIZE_SECTION_HEADER = 10
SIZE_BODY = 10

# Margins: \usepackage[top=0.5in, bottom=0.5in, left=0.6in, right=0.6in]{geometry}
MARGIN_TOP = 36  # 0.5in
MARGIN_BOTTOM = 36  # 0.5in
MARGIN_LEFT = 43.2  # 0.6in
MARGIN_RIGHT = 43.2  # 0.6in

PAGE_WIDTH = 612
PAGE_HEIGHT = 792
CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
CONTENT_RIGHT = PAGE_WIDTH - MARGIN_RIGHT

# \setlist[itemize]{leftmargin=12pt, itemsep=1pt, parsep=0pt, topsep=2pt}
BULLET_LEFT_INDENT = 12
BULLET_ITEM_SPACING = 1
BULLET_TOP_SPACING = 2

# \titlespacing{\section}{0pt}{8pt}{4pt}, rule is \rule{\linewidth}{0.5pt}
SECTION_SPACE_BEFORE = 8
SECTION_SPACE_AFTER = 4
SECTION_RULE_WIDTH = 0.5

# \newcommand{\jobheader}: \vspace{4pt} before, \vspace{1pt} after
JOB_SPACING_BEFORE = 4
JOB_SPACING_AFTER = 1

# \skillrow: trailing \\[2pt]
SKILL_ROW_SPACING = 2

LINE_HEIGHT = 1.15  # LaTeX's default single-spacing leading multiplier


def _sanitize_for_filename(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "_", text.strip())
    return text.strip("_") or "Unknown"


def build_resume_filename(company: str, job_title: str, output_dir: str = OUTPUT_DIR) -> str:
    today = date.today().isoformat()
    filename = f"Resume_{_sanitize_for_filename(company)}_{_sanitize_for_filename(job_title)}_{today}.pdf"
    return os.path.join(output_dir, filename)


class ResumeDocument:
    def __init__(self):
        self.pdf = FPDF(format="Letter", unit="pt")
        self.pdf.set_margins(MARGIN_LEFT, MARGIN_TOP, MARGIN_RIGHT)
        self.pdf.set_auto_page_break(auto=False)
        self.pdf.add_page()
        self.pdf.set_text_color(*BLACK)
        for style, path in FONT_FILES.items():
            self.pdf.add_font("Arial", style, path)

    def _set_font(self, style: str = "", size: float = SIZE_BODY) -> None:
        self.pdf.set_font("Arial", style, size)

    def name(self, text: str) -> None:
        self._set_font("B", SIZE_NAME)
        self.pdf.cell(
            CONTENT_WIDTH,
            SIZE_NAME * LINE_HEIGHT,
            text,
            align="C",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

    def contact_line(self, parts: list[str]) -> None:
        self._set_font("", SIZE_CONTACT)
        text = "    |    ".join(parts)
        self.pdf.cell(
            CONTENT_WIDTH,
            SIZE_CONTACT * LINE_HEIGHT + 4,
            text,
            align="C",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

    def profile_summary(self, text: str) -> None:
        self._set_font("", SIZE_BODY)
        self.pdf.multi_cell(
            CONTENT_WIDTH,
            SIZE_BODY * LINE_HEIGHT,
            text,
            align="J",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

    def section_header(self, text: str) -> None:
        self.pdf.ln(SECTION_SPACE_BEFORE)
        self._set_font("B", SIZE_SECTION_HEADER)
        self.pdf.set_x(MARGIN_LEFT)
        self.pdf.cell(
            CONTENT_WIDTH,
            SIZE_SECTION_HEADER * LINE_HEIGHT,
            text.upper(),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        y = self.pdf.get_y()
        self.pdf.set_draw_color(*BLACK)
        self.pdf.set_line_width(SECTION_RULE_WIDTH)
        self.pdf.line(MARGIN_LEFT, y, CONTENT_RIGHT, y)
        self.pdf.ln(SECTION_SPACE_AFTER)

    def job_header(self, title: str, company: str, dates: str) -> None:
        self.pdf.ln(JOB_SPACING_BEFORE)
        y = self.pdf.get_y()
        row_h = SIZE_BODY * LINE_HEIGHT

        self.pdf.set_xy(MARGIN_LEFT, y)
        self._set_font("B", SIZE_BODY)
        self.pdf.write(row_h, title + "  ")
        self._set_font("I", SIZE_BODY)
        self.pdf.write(row_h, company)

        self._set_font("", SIZE_BODY)
        date_width = self.pdf.get_string_width(dates)
        self.pdf.set_xy(CONTENT_RIGHT - date_width, y)
        self.pdf.cell(date_width, row_h, dates, align="R")

        self.pdf.set_xy(MARGIN_LEFT, y + row_h)
        self.pdf.ln(JOB_SPACING_AFTER)

    def italic_line(self, text: str, size: float = SIZE_CONTACT) -> None:
        self._set_font("I", size)
        self.pdf.set_x(MARGIN_LEFT)
        self.pdf.multi_cell(
            CONTENT_WIDTH, size * LINE_HEIGHT, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT
        )

    def start_bullet_list(self) -> None:
        self.pdf.ln(BULLET_TOP_SPACING)

    def end_bullet_list(self) -> None:
        self.pdf.ln(BULLET_TOP_SPACING)

    def _bullet_glyph(self) -> None:
        self.pdf.set_x(MARGIN_LEFT)
        self._set_font("", SIZE_BODY)
        self.pdf.cell(
            BULLET_LEFT_INDENT,
            SIZE_BODY * LINE_HEIGHT,
            "•",
            new_x=XPos.RIGHT,
            new_y=YPos.TOP,
        )
        self.pdf.set_x(MARGIN_LEFT + BULLET_LEFT_INDENT)

    def bullet(self, text: str) -> None:
        self._bullet_glyph()
        self._set_font("", SIZE_BODY)
        self.pdf.multi_cell(
            CONTENT_WIDTH - BULLET_LEFT_INDENT,
            SIZE_BODY * LINE_HEIGHT,
            text,
            align="J",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        self.pdf.ln(BULLET_ITEM_SPACING)

    def bullet_bold(self, lead: str, rest: str) -> None:
        self._bullet_glyph()
        self._set_font("", SIZE_BODY)
        combined = f"**{lead}:** {rest}"
        self.pdf.multi_cell(
            CONTENT_WIDTH - BULLET_LEFT_INDENT,
            SIZE_BODY * LINE_HEIGHT,
            combined,
            align="J",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            markdown=True,
        )
        self.pdf.ln(BULLET_ITEM_SPACING)

    def skill_row(self, category: str, items: list[str]) -> None:
        self.pdf.set_x(MARGIN_LEFT)
        self._set_font("", SIZE_BODY)
        combined = f"**{category}:** " + ", ".join(items)
        self.pdf.multi_cell(
            CONTENT_WIDTH,
            SIZE_BODY * LINE_HEIGHT,
            combined,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            markdown=True,
        )
        self.pdf.ln(SKILL_ROW_SPACING)

    def overflowed(self) -> bool:
        return self.pdf.get_y() > PAGE_HEIGHT - MARGIN_BOTTOM

    def save(self, path: str) -> None:
        self.pdf.output(path)


def render_resume(data: dict, output_path: str) -> bool:
    doc = ResumeDocument()

    doc.name(data["name"])
    doc.contact_line(data["contact"])

    doc.section_header("Profile Summary")
    doc.profile_summary(data["profile_summary"])

    doc.section_header("Education")
    for entry in data["education"]:
        doc.job_header(entry["degree"], entry["school"], entry["dates"])
        if entry.get("note"):
            doc.italic_line(entry["note"])

    if data.get("open_source"):
        doc.section_header("Open Source")
        for entry in data["open_source"]:
            row_h = SIZE_BODY * LINE_HEIGHT
            doc.pdf.set_x(MARGIN_LEFT)
            doc._set_font("B", SIZE_BODY)
            doc.pdf.write(row_h, entry["name"] + "  ")
            doc._set_font("I", SIZE_BODY)
            doc.pdf.write(row_h, entry["url"])
            doc.pdf.ln(row_h)
            doc.start_bullet_list()
            for bullet_text in entry["bullets"]:
                doc.bullet(bullet_text)
            doc.end_bullet_list()

    doc.section_header("Experience")
    for job in data["experience"]:
        doc.job_header(job["title"], job["company"], job["dates"])
        doc.start_bullet_list()
        for b in job["bullets"]:
            if isinstance(b, (list, tuple)):
                doc.bullet_bold(b[0], b[1])
            else:
                doc.bullet(b)
        doc.end_bullet_list()

    doc.section_header("Technical Skills")
    for category, items in data["skills"]:
        doc.skill_row(category, items)

    fits_one_page = not doc.overflowed()
    doc.save(output_path)
    return fits_one_page


def render_resume_fit_one_page(data: dict, output_path: str, max_attempts: int = 15) -> bool:
    import copy

    working_data = copy.deepcopy(data)

    for _ in range(max_attempts):
        fits = render_resume(working_data, output_path)
        if fits:
            return True

        experience = working_data.get("experience", [])
        candidate = max(
            (job for job in experience if job["bullets"]),
            key=lambda job: len(job["bullets"]),
            default=None,
        )
        if candidate is None:
            break
        candidate["bullets"].pop()

    return False


if __name__ == "__main__":
    sample_data = {
        "name": "SHARDUL JANASKAR",
        "contact": [
            "Chicago, IL",
            "773-517-1380",
            "shardul2607@gmail.com",
            "linkedin.com/in/sharduljanaskar",
            "github.com/ShardulJ",
        ],
        "profile_summary": (
            "Senior ML engineer with 5+ years building and deploying production AI "
            "systems end to end, with a strong focus on LLM fine tuning, agentic "
            "architectures, evaluation frameworks, and MLOps infrastructure. Hands on "
            "experience with PyTorch, HuggingFace, Docker, Kubernetes, and AWS across "
            "the full ML lifecycle. I pick up new tools quickly, work well across "
            "engineering and product teams, and care about building things that hold "
            "up in production."
        ),
        "education": [
            {
                "degree": "Master's in Computer Science",
                "school": "DePaul University, Chicago, IL",
                "dates": "Sep 2023 to Jun 2025",
                "note": (
                    "Relevant Coursework: Deep Learning, Statistical Machine "
                    "Learning, NLP, Time Series Analysis, Algorithms"
                ),
            }
        ],
        "experience": [
            {
                "title": "AI/ML Engineer (Volunteer)",
                "company": "ChiEAC NGO",
                "dates": "Nov 2025 to Present",
                "bullets": [
                    (
                        "Built production LLM system with two tier routing and RAG "
                        "pipeline",
                        "intent classifier routing queries between a large model and "
                        "a fine tuned small model, selective context injection "
                        "grounding outputs in live data, output validation "
                        "guardrails blocking unsafe responses.",
                    ),
                    (
                        "Developed SFT and DPO fine tuning pipeline with rigorous "
                        "evaluation",
                        "LoRA adapters on PyTorch, three dimensional LLM as judge "
                        "evaluation across 150 golden test cases, improved safety "
                        "scores from 3.1 to 4.6, reduced failures 40 percent.",
                    ),
                    (
                        "Built full MLOps infrastructure from scratch",
                        "DVC dataset versioning, MLflow experiment tracking, CI/CD "
                        "with GitHub Actions, shadow and canary deployment, "
                        "automated rollback, p50/p95/p99 latency monitoring, drift "
                        "detection.",
                    ),
                ],
            },
            {
                "title": "Research Assistant",
                "company": "DePaul University",
                "dates": "Dec 2023 to Nov 2025",
                "bullets": [
                    (
                        "Built self supervised multimodal system combining vision, "
                        "audio, and video",
                        "DINO based vision transformer with audio and video signal "
                        "processing, embedding based retrieval and semantic "
                        "clustering, improved accuracy 28 percent and processing "
                        "time 40 percent.",
                    ),
                    "Designed evaluation benchmarks and scalable data pipelines, "
                    "optimized inference achieving 3.2x throughput improvement, "
                    "collaborated across interdisciplinary teams.",
                ],
            },
            {
                "title": "Associate Machine Learning Engineer",
                "company": "Netscribes India Pvt. Ltd.",
                "dates": "Mar 2021 to Dec 2022",
                "bullets": [
                    (
                        "Built production ML systems serving 10K+ users at 99.2 "
                        "percent uptime",
                        "PySpark on Databricks processing tens of millions of "
                        "records, XGBoost ranking with SHAP feature importance, A/B "
                        "testing infrastructure, drift detection, improved "
                        "engagement 88 percent.",
                    ),
                    "Caught silent model regression through category level "
                    "monitoring that aggregate metrics missed. Built schema "
                    "contract tests preventing recurrence. Mentored two junior "
                    "engineers.",
                ],
            },
            {
                "title": "Machine Learning Engineer",
                "company": "Freelance",
                "dates": "Jan 2019 to Mar 2021",
                "bullets": [
                    (
                        "Built and deployed ML systems for 10+ clients across "
                        "manufacturing, agriculture, and e commerce",
                        "time series forecasting on sensor data, Airflow ETL "
                        "pipelines integrating Salesforce CRM, Google Analytics, "
                        "and S3, real time inference APIs on AWS Lambda.",
                    ),
                ],
            },
            {
                "title": "Project Research Intern",
                "company": "Qure.ai",
                "dates": "Nov 2018 to Jan 2019",
                "bullets": [
                    "Built a CNN based medical image classifier in a regulated "
                    "healthcare environment, improved accuracy from 43 percent to "
                    "66 percent through architecture optimization and CLAHE "
                    "preprocessing for cross device generalization.",
                ],
            },
        ],
        "skills": [
            (
                "LLM and Agentic Systems",
                [
                    "Fine tuning (SFT, DPO, LoRA, QLoRA)",
                    "PEFT",
                    "TRL",
                    "HuggingFace",
                    "RAG Pipelines",
                    "Agentic Workflows",
                    "Prompt Engineering",
                    "Output Validation",
                ],
            ),
            (
                "ML and Deep Learning",
                [
                    "PyTorch",
                    "XGBoost",
                    "Scikit-learn",
                    "CNNs",
                    "Vision Transformers",
                    "Self-supervised Learning",
                    "NLP",
                    "Time Series",
                    "Clustering",
                    "SHAP",
                ],
            ),
            (
                "MLOps and Infrastructure",
                [
                    "Python",
                    "Docker",
                    "Kubernetes",
                    "AWS",
                    "FastAPI",
                    "Airflow",
                    "PySpark",
                    "Databricks",
                    "MLflow",
                    "DVC",
                    "W&B",
                    "CI/CD",
                    "GitHub Actions",
                    "SQL",
                ],
            ),
        ],
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = build_resume_filename("Reference", "LaTeX Match Test")
    fits = render_resume(sample_data, output_path)
    print(f"Saved to {output_path}")
    print(f"Fits on one page: {fits}")
