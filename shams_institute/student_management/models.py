from django.db import models
from datetime import date, timedelta
from django.core.exceptions import ValidationError


# Course Model 
class Course(models.Model):
    name = models.CharField(max_length=100)  # e.g., Ms. Office, English Language
    duration_months = models.IntegerField()  # Duration in months
    fees = models.DecimalField(max_digits=10, decimal_places=2)  # Course fees
    requires_lab = models.BooleanField(default=False)  # New field to indicate if the course requires a lab
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

# Lab Model
class Lab(models.Model):
    name = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField()

    def __str__(self):
        return self.name

# Slot Model
class Slot(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)  # Link to Course
    instructor = models.CharField(max_length=100)  # Instructor name
    start_time = models.TimeField()  # Slot start time
    end_time = models.TimeField()  # Slot end time
    max_students = models.PositiveIntegerField()  # Maximum students per slot
    current_students = models.PositiveIntegerField(default=0)  # Track enrolled students
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, null=True, blank=True)  # Reference to Lab
    
    def __str__(self):
        return f"{self.course.name} - {self.start_time.strftime('%I:%M %p')} to {self.end_time.strftime('%I:%M %p')} (Instructor: {self.instructor})"

    def is_full(self): # Check Slot is Full, and Required Lab
        if self.course.requires_lab:
            if self.lab:
                total_students_in_lab = Slot.objects.filter(
                    lab=self.lab,
                    start_time=self.start_time,
                    end_time=self.end_time
                ).aggregate(total=models.Sum('current_students'))['total'] or 0
                if total_students_in_lab >= self.lab.capacity:
                    return True
            else:
                raise ValidationError(f"The course {self.course.name} requires a lab, but no lab is assigned to this slot.")
        return self.current_students >= self.max_students

    def mark_attendance(self, student_id, date, status): # Mark Attendance
        enrollment = Enrollment.objects.filter(student__student_id=student_id, slot=self).first()
        if enrollment:
            Attendance.objects.create(enrollment=enrollment, date=date, status=status)
        else:
            raise ValidationError(f"No enrollment found for student ID {student_id} in this slot.")
        
# Student Model
class Student(models.Model):
    name = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100)
    phone_no = models.CharField(max_length=15)
    age = models.IntegerField()
    school = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField()
    admission_date = models.DateField(auto_now_add=True)
    student_id = models.CharField(max_length=10, unique=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.student_id})"

    def save(self, *args, **kwargs):
        if not self.student_id:
            self.student_id = self.generate_student_id()
        super().save(*args, **kwargs)

    def generate_student_id(self):
        current_date = date.today()
        month_abbr = current_date.strftime('%b').upper()
        year = current_date.strftime('%y')
        last_student = Student.objects.filter(student_id__startswith=f"{month_abbr}{year}").order_by('student_id').last()
        if last_student:
            last_id = int(last_student.student_id[-3:])
            new_id = last_id + 1
        else:
            new_id = 1
        return f"{month_abbr}{year}{new_id:03d}"

# Enrollment Model
class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE)
    enrollment_date = models.DateField()
    fees_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_fees = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_type = models.CharField(max_length=20, choices=[('monthly', 'Monthly'), ('package', 'Package')])
    is_paid = models.BooleanField(default=False)
    last_payment_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.name} ({self.student.student_id}) - {self.course.name}"

    def calculate_monthly_fee(self):
        """Calculate the monthly fee based on the total fees and course duration."""
        return (self.course.fees - self.discount)

    def calculate_total_fees(self):
        """Calculate the total fees based on the course fees, duration, and discount."""
        return self.calculate_monthly_fee() * self.course.duration_months

    def create_monthly_fees(self):
        """Create monthly fee records for the entire course duration."""
        monthly_fee = self.calculate_monthly_fee()
        for month in range(self.course.duration_months):
            due_date = self.enrollment_date + timedelta(days=30 * month)
            Fee.objects.create(
                enrollment=self,
                due_date=due_date,
                amount=monthly_fee,
            )

    def save(self, *args, **kwargs):
        """Override the save method to calculate total fees and create monthly fees when an enrollment is created."""
        if self.slot.is_full():
            raise ValidationError(f"The slot for {self.slot.course.name} is full.")

        self.total_fees = self.calculate_total_fees()
        is_new = self._state.adding  # Check if this is a new enrollment
        super().save(*args, **kwargs)
        if is_new:
            self.slot.current_students += 1
            self.slot.save()
            if self.payment_type == 'monthly':
                self.create_monthly_fees()

    def delete(self, *args, **kwargs):
        """Override the delete method to update the slot's current_students count."""
        if not hasattr(self, '_skip_slot_update'):
            self.slot.current_students -= 1
            self.slot.save()
        super().delete(*args, **kwargs)

    @staticmethod
    def remove_finished_enrollments():
        today = date.today()
        finished_enrollments = Enrollment.objects.filter(
            enrollment_date__lte=today - timedelta(days=30 * models.F('course__duration_months'))
        )
        for enrollment in finished_enrollments:
            FinalTest.objects.create(
                student=enrollment.student,
                course=enrollment.course,
                test_date=today
            )
            enrollment._skip_slot_update = True
            enrollment.delete()
# Fee Model
class Fee(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    due_date = models.DateField()  # Due date for the fee (e.g., 10th of each month)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Fee amount
    is_paid = models.BooleanField(default=False)  # Whether the fee is paid
    payment_date = models.DateField(null=True, blank=True)  # Date when the fee was paid

    def __str__(self):
        return f"{self.enrollment.student.name} ({self.enrollment.student.student_id}) - {self.due_date} - {'Paid' if self.is_paid else 'Unpaid'}"

    def clean(self):
        """
        Ensure the amount paid does not exceed the fee amount.
        """
        if hasattr(self, 'amount_paid') and self.amount_paid > self.amount:
            raise ValidationError(f"Amount paid cannot exceed the fee amount of {self.amount}.")

    def save(self, *args, **kwargs):
        """
        Override the save method to update the Fee record when a payment is made.
        """
        self.clean()  # Validate before saving
        super().save(*args, **kwargs)

        # Update the enrollment's fees_paid and is_paid status
        if self.is_paid:
            self.enrollment.fees_paid += self.amount
            self.enrollment.last_payment_date = self.payment_date
            if self.enrollment.fees_paid >= self.enrollment.total_fees:
                self.enrollment.is_paid = True
            self.enrollment.__class__.objects.filter(pk=self.enrollment.pk).update(
                fees_paid=self.enrollment.fees_paid,
                last_payment_date=self.enrollment.last_payment_date,
                is_paid=self.enrollment.is_paid
            )
        else:
            self.enrollment.is_paid = False
            self.enrollment.__class__.objects.filter(pk=self.enrollment.pk).update(
                is_paid=self.enrollment.is_paid
            )
# Attendance Model
class Attendance(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=[('present', 'Present'), ('absent', 'Absent')])

    def __str__(self):
        return f"{self.enrollment.student.name} ({self.enrollment.student.student_id}) - {self.date}"
    
# Income Expense Model
class IncomeExpense(models.Model):
    date = models.DateField()
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=10, choices=[('income', 'Income'), ('expense', 'Expense')])

    def __str__(self):
        return f"{self.description} - {self.amount}"
    
# Final Test Model
class FinalTest(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    test_date = models.DateField()
    grade = models.CharField(max_length=2, blank=True, null=True)
    test_attendance = models.BooleanField(default=False)
    test_done = models.BooleanField(default=False)
    retest = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.name} - {self.course.name} - {self.test_date}"

    def save(self, *args, **kwargs):
        if self.test_done and not self.retest:
            # Add the student to the CourseCompletion model
            CourseCompletion.objects.create(
                student=self.student,
                course=self.course,
                enrollment_date=self.student.enrollment_set.filter(course=self.course).first().enrollment_date,
                course_completion_date=date.today(),
                final_test_date=self.test_date,
                grade=self.grade,
                certificate_fee=0,  # Default value, can be updated later
                certificate_taken=False  # Default value, can be updated later
            )
            # Update the slot's current_students count
            slot = self.student.enrollment_set.filter(course=self.course).first().slot
            slot.current_students -= 1
            slot.save()
            # Remove the student from the final test
            self.delete()
        elif self.retest:
            # Add the student to the final test again
            FinalTest.objects.create(
                student=self.student,
                course=self.course,
                test_date=date.today()
            )
        else:
            super().save(*args, **kwargs)

# Course Completion Model
class CourseCompletion(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrollment_date = models.DateField()
    course_completion_date = models.DateField()
    final_test_date = models.DateField()
    grade = models.CharField(max_length=2, blank=True, null=True)
    certificate_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    certificate_taken = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.name} - {self.course.name} - {self.course_completion_date}"

