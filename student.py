# TODO: 
#  Purpose:
      #Manage student records and past performance.
      
      #Features:
      
      #Register students (name, ID, email, program, level).
      
      #Keep a transcript (list of completed courses + grades).
      
      #Allow students to view their academic history.
      
      #Prevent duplicate student IDs.
      
      #Database Tables:
      
      #students
      
      #transcripts
      
      #Example error:
      
      #"Student ID already exists"
      #"Please select a valid program"
class Student:
    
    def __init__(self, student_id, name, email, program, level, transcript=None):
        self.student_id = student_id
        self.name = name
        self.email = email
        self.program = program
        self.level = level
        self.CreditHours = 0
        self.transcript = transcript or []
    
    
    def getCreditHours(self,All_Courses):
        total = 0
        for course_code in self.transcript:
            if course_code in All_Courses:
                total += All_Courses[course_code].credits
        return total
    def add_to_transcript(self,course_code):
        if course_code not in self.transcript:
            self.transcript.append(course_code)
