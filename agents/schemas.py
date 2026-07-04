from pydantic import BaseModel, Field

class MatchedExam(BaseModel):
    file_id: str = Field(description="Google Drive file ID")
    file_name: str = Field(description="Display name of the exam file")
    course_name: str | None = Field(default=None, description="The name of the course")

class IdentifierOutput(BaseModel):
    """Output schema for the Identifier Agent"""
    matched_exams: list[MatchedExam] = Field(default_factory=list, description="List of exams matched to the target lecturer")
class Question(BaseModel):
    q_number: int = Field(default=0, description="The number of the question")
    tags: list[str] = Field(default_factory=list, description="1-3 tags based on the topics mentioned in the syllabus")
    type: str = Field(default="open_ended", description="Question type: multiple_choice, open_ended, calculation, proof, short_answer")

class ExamStructure(BaseModel):
    file_name: str = Field(default="Unknown", description="The name of the exam file")
    document_type: str = Field(default="exam", description="Must be 'exam'")
    total_questions: int = Field(default=0, description="Total number of questions in the exam")
    questions: list[Question] = Field(default_factory=list, description="List of questions in the exam")

class ScoreDeduction(BaseModel):
    q_number: int = Field(default=0, description="The number of the question where points were deducted")
    mistake: str = Field(default="", description="The mistake the student made")
    deduction_reason: str = Field(default="", description="The reason the score was lowered")

class StudentSolution(BaseModel):
    file_name: str = Field(default="Unknown", description="The name of the student solution file")
    document_type: str = Field(default="student_solution", description="Must be 'student_solution'")
    score_deductions: list[ScoreDeduction] = Field(default_factory=list, description="List of score deductions in the solution")

class DocumentProcessingOutput(BaseModel):
    """Output schema for the Document Processing Agent"""
    exams: list[ExamStructure] = Field(default_factory=list, description="List of analyzed exams")
    student_solutions: list[StudentSolution] = Field(default_factory=list, description="List of analyzed student solutions")

class FinalReport(BaseModel):
    """Output schema for the Pattern Synthesizer Agent"""
    summary: str = Field(description="Detailed summary report covering recurring topics, question style, and study recommendations, including mistakes based on score deductions with source citations.")
    exams: list[ExamStructure] = Field(default_factory=list, description="List of analyzed exams, preserving the per-question breakdown")
    student_solutions: list[StudentSolution] = Field(default_factory=list, description="List of analyzed student solutions and score deductions")
