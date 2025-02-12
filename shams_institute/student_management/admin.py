from django.contrib import admin
from .models import Course, CourseCompletion, Fee, Lab, Slot, Student, Enrollment, Attendance, IncomeExpense, FinalTest, CourseCompletion
from django.core.exceptions import ValidationError
from django.contrib import messages
from datetime import date, timedelta
from django.db.models import F
from django.contrib.auth.models import User

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'student_id', 'course', 'slot', 'enrollment_date', 'fees_paid', 'payment_type', 'is_paid')
    search_fields = ('student__name', 'student__student_id', 'course__name')
    actions = ['remove_finished_enrollments']

    def save_model(self, request, obj, form, change):
        try:
            obj.save()
        except ValidationError as e:
            self.message_user(request, e.message, level=messages.ERROR)

    def remove_finished_enrollments(self, request, queryset):
        today = date.today()
        count = 0
        for enrollment in queryset:
            course_duration_days = enrollment.course.duration_months * 30
            if enrollment.enrollment_date <= today - timedelta(days=course_duration_days):
                FinalTest.objects.create(
                    student=enrollment.student,
                    course=enrollment.course,
                    test_date=today
                )
                enrollment.delete()
                count += 1
        self.message_user(request, f'Successfully removed {count} finished enrollments', level=messages.SUCCESS)





admin.site.unregister(User)

admin.site.register(Course)
admin.site.register(Slot)
admin.site.register(Student)
admin.site.register(Attendance)
admin.site.register(IncomeExpense)
admin.site.register(Fee)
admin.site.register(FinalTest)
admin.site.register(CourseCompletion)
admin.site.register(Lab)
