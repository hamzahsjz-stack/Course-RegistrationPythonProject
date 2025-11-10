
# TODO:
#Purpose:
#Let administrators define and manage all course data.

#Features:

#Add/edit/delete courses:

#Course code, name, credits, lecture hours, lab hours, prerequisites, max capacity.

#Link courses to specific programs and levels (e.g., Computer L3 S1).

#Validate all inputs:

#No duplicate course codes.

#Credit hours must be positive.

#Prerequisites must exist in system.

#Bulk import via CSV/Excel.

#Stored in Database Tables:

#courses

#program_plans

#prerequisites

#Errors displayed as messages:

#"Course code COE310 already exists"
#"Prerequisite COE200 not found"
from student import Student
class Course:
    def __init__(self,code,name,credits,hours,lecture_hours,lab_hours,max_capacity,prerequisites=None):
        self.code = code
        self.name = name
        self.credits = credits
        self.hours = hours
        self.lecture_hours = lecture_hours
        self.lab_hours = lab_hours
        self.max_capacity = max_capacity
        self.prerequisites = prerequisites or []
        self.enrolled_Students = 0
    def isFull(self):
        #check if the course has the max enrolled students if true return true if false return false
        return self.enrolled_Students >= self.max_capacity
    def CheckPrerequisites(self, student_transcript):
        # """Return True if all prerequisites are met.""" 
        return all(p in student_transcript for p in self.prerequisites)
    
