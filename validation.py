# TODO:
#Purpose:
      #The core of the system — allows students to register for courses and checks every rule automatically.
      
      #Validation checks include:
      
      #Total credits within limits (e.g., 12–18 hours).
      
      #Prerequisites completed.
      
      #Courses belong to the student’s program & level.
      
      #No schedule conflicts (lectures/labs overlap).
      
      #Course capacity not exceeded.
      
      #Output:
      
      #A color-coded weekly timetable.
      
      #Validation messages explaining any errors.
      
      #Successful registrations stored in registrations table.
      
      #Example errors:
      
      #"Cannot register for COE310: prerequisite COE200 not completed"
      #"Schedule conflict: COE310 Lab overlaps with COE320 Lecture"
      #"Credit limit exceeded (20 > 18 hours)"
      
      #Bonus Feature:
      #Waitlist system → if a course is full, the student gets added to a waiting list.
