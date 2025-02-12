from django import forms
from .models import Enrollment, Fee, Attendance, FinalTest, Student, Course, Slot

class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['student', 'course', 'slot', 'enrollment_date', 'discount', 'payment_type']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slot'].queryset = Slot.objects.none()  # Default to empty

        if 'course' in self.data:
            try:
                course_id = int(self.data.get('course'))
                self.fields['slot'].queryset = Slot.objects.filter(course_id=course_id).order_by('start_time')
            except (ValueError, TypeError):
                self.fields['slot'].queryset = Slot.objects.none()
        elif self.instance.pk:
            self.fields['slot'].queryset = self.instance.course.slot_set.order_by('start_time')


class FeeForm(forms.ModelForm):
    class Meta:
        model = Fee
        fields = ['payment_date', 'amount', 'is_paid']

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        enrollment = self.instance.enrollment
        remaining_fees = enrollment.total_fees - enrollment.fees_paid
        
        if amount > remaining_fees:
            raise forms.ValidationError(f"Amount paid cannot exceed the remaining fees of {remaining_fees}.")
        
        return amount

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['date', 'status']

class FinalTestForm(forms.ModelForm):
    class Meta:
        model = FinalTest
        fields = ['test_date','grade', 'test_attendance', 'test_done', 'retest']

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        exclude = ['student_id', 'admission_date']

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = '__all__'

class SlotForm(forms.ModelForm):
    class Meta:
        model = Slot
        fields = '__all__'

