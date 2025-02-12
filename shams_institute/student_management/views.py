from django.db import models
from django.shortcuts import render, get_object_or_404, redirect
from .models import Enrollment, Fee, Attendance, IncomeExpense, Student, Slot, FinalTest, Course, Lab
from .forms import EnrollmentForm, FeeForm, AttendanceForm, FinalTestForm, StudentForm, CourseForm, SlotForm
from django.http import HttpResponse, JsonResponse
from reportlab.pdfgen import canvas
from django.contrib import messages
from django.core.exceptions import ValidationError
from datetime import date, timedelta, datetime
from django.db.models import Sum, Q
from django.utils.timezone import localtime

# View to enroll a student
def enroll_student(request):
    if request.method == 'POST':
        form = EnrollmentForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                return render(request, 'success.html')
            except ValidationError as e:
                form.add_error(None, e)
    else:
        form = EnrollmentForm()
    return render(request, 'enroll.html', {'form': form})

# View to record a fee payment
def record_fee_payment(request, fee_id):
    fee = get_object_or_404(Fee, id=fee_id)
    if request.method == 'POST':
        form = FeeForm(request.POST, instance=fee)
        if form.is_valid():
            fee = form.save(commit=False)
            if fee.amount > fee.enrollment.total_fees - fee.enrollment.fees_paid:
                messages.error(request, "Amount paid cannot exceed the remaining fees.")
                return redirect('record_fee_payment', fee_id=fee_id)
            fee.is_paid = True
            fee.payment_date = date.today()
            fee.save()
            messages.success(request, "Fee payment recorded successfully!")
            return redirect('record_fee_payment', fee_id=fee_id)
    else:
        form = FeeForm(instance=fee)
    return render(request, 'fee_payment.html', {'form': form, 'fee': fee})

# View to record attendance for a student
def record_attendance(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    if request.method == 'POST':
        status = request.POST.get('status')
        date_str = request.POST.get('date')
        try:
            attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            try:
                attendance_date = datetime.strptime(date_str, '%b. %d, %Y').date()
            except ValueError:
                messages.error(request, "Invalid date format.")
                return redirect('daily_attendance_report')
        Attendance.objects.create(enrollment=enrollment, date=attendance_date, status=status)
        messages.success(request, "Attendance recorded successfully!")
        return redirect('daily_attendance_report')
    return render(request, 'record_attendance.html', {'enrollment': enrollment})

# View to display the dashboard with summary statistics
def dashboard(request):
    total_students = Student.objects.count()
    total_fees_collected = Fee.objects.filter(is_paid=True).aggregate(total=Sum('amount'))['total'] or 0
    today = date.today()
    first_day_of_month = today.replace(day=1)
    pending_fees = Fee.objects.filter(is_paid=False, due_date__gte=first_day_of_month, due_date__lte=today).aggregate(total=Sum('amount'))['total'] or 0
    context = {
        'total_students': total_students,
        'total_fees_collected': total_fees_collected,
        'pending_fees': pending_fees,
    }
    return render(request, 'dashboard.html', context)

# View to generate a PDF fee receipt
def generate_fee_receipt(request, fee_id):
    fee = get_object_or_404(Fee, id=fee_id)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="fee_receipt_{fee.id}.pdf"'
    p = canvas.Canvas(response)
    p.drawString(100, 750, f"Fee Receipt for {fee.enrollment.student.name}")
    p.drawString(100, 730, f"Course: {fee.enrollment.course.name}")
    p.drawString(100, 710, f"Amount Paid: {fee.amount}")
    p.drawString(100, 690, f"Payment Date: {fee.payment_date}")
    p.drawString(100, 670, f"Due Date: {fee.due_date}")
    p.showPage()
    p.save()
    return response

# View to display the daily fee report
def daily_fee_report(request):
    today = date.today()
    unpaid_fees = Fee.objects.filter(is_paid=False, due_date__lte=today).order_by('due_date')
    students_with_unpaid_fees = Student.objects.filter(enrollment__fee__is_paid=False, enrollment__fee__due_date__lte=today).distinct()
    context = {
        'unpaid_fees': unpaid_fees,
        'students_with_unpaid_fees': students_with_unpaid_fees,
        'today': today,
    }
    return render(request, 'daily_fee_report.html', context)

# View to display the course slots report
def course_slots_report(request):
    slots = Slot.objects.all()
    report_data = []
    for slot in slots:
        if slot.course.requires_lab and slot.lab:
            total_students_in_lab = Slot.objects.filter(lab=slot.lab, start_time=slot.start_time, end_time=slot.end_time).aggregate(total=models.Sum('current_students'))['total'] or 0
            available_seats = slot.lab.capacity - total_students_in_lab
        else:
            available_seats = slot.max_students - slot.current_students
        next_available_date = None
        if slot.is_full():
            next_available_enrollment = Enrollment.objects.filter(slot=slot).order_by('enrollment_date').first()
            if next_available_enrollment:
                next_available_date = next_available_enrollment.enrollment_date + timedelta(days=30 * slot.course.duration_months)
        students = Enrollment.objects.filter(slot=slot).select_related('student', 'course')
        student_data = []
        for enrollment in students:
            course_end_date = enrollment.enrollment_date + timedelta(days=30 * enrollment.course.duration_months)
            student_data.append({
                'name': enrollment.student.name,
                'student_id': enrollment.student.student_id,
                'enrollment_date': enrollment.enrollment_date,
                'course_end_date': course_end_date,
            })
        report_data.append({
            'slot_id': slot.id,
            'course_name': slot.course.name,
            'instructor': slot.instructor,
            'start_time': slot.start_time,
            'end_time': slot.end_time,
            'available_seats': available_seats,
            'next_available_date': next_available_date,
            'students': student_data,
        })
    return render(request, 'course_slots_report.html', {'report_data': report_data})

# View to display details of a specific course slot
def course_slot_details(request, slot_id):
    slot = get_object_or_404(Slot, id=slot_id)
    enrollments = Enrollment.objects.filter(slot=slot).select_related('student', 'course')
    student_data = []
    for enrollment in enrollments:
        course_end_date = enrollment.enrollment_date + timedelta(days=30 * enrollment.course.duration_months)
        student_data.append({
            'name': enrollment.student.name,
            'student_id': enrollment.student.student_id,
            'enrollment_date': enrollment.enrollment_date,
            'course_end_date': course_end_date,
        })
    
    if slot.course.requires_lab and slot.lab:
        total_students_in_lab = Slot.objects.filter(lab=slot.lab, start_time=slot.start_time, end_time=slot.end_time).aggregate(total=models.Sum('current_students'))['total'] or 0
        available_seats = slot.lab.capacity - total_students_in_lab
    else:
        available_seats = slot.max_students - slot.current_students

    return render(request, 'course_slot_details.html', {
        'slot': slot,
        'students': student_data,
        'available_seats': available_seats,
    })

# View to display the daily attendance report
def daily_attendance_report(request):
    today = date.today()
    current_time = localtime().time()
    slots = Slot.objects.filter(start_time__lte=current_time, end_time__gte=current_time).order_by('start_time')
    report_data = []
    for slot in slots:
        enrollments = Enrollment.objects.filter(slot=slot)
        students = []
        for enrollment in enrollments:
            attendance_record = Attendance.objects.filter(enrollment=enrollment, date=today).first()
            students.append({
                'name': enrollment.student.name,
                'student_id': enrollment.student.student_id,
                'course': enrollment.course.name,
                'enrollment_id': enrollment.id,
                'attendance_marked': attendance_record is not None,
                'attendance_status': attendance_record.status if attendance_record else None,
            })
        report_data.append({
            'slot': slot,
            'students': students,
        })
    return render(request, 'daily_attendance_report.html', {'report_data': report_data, 'today': today})

# View to display the final test report and handle updates
def final_test_report(request):
    final_tests = FinalTest.objects.all()
    if request.method == 'POST':
        final_test_id = request.POST.get('id')
        final_test = get_object_or_404(FinalTest, id=final_test_id)
        form = FinalTestForm(request.POST, instance=final_test)
        if form.is_valid():
            form.save()
            messages.success(request, "Final test updated successfully!")
            return redirect('final_test_report')
    else:
        form = FinalTestForm()
    return render(request, 'final_test_report.html', {'final_tests': final_tests, 'form': form})

# View to display the list of students

def student_list(request):
    query_name = request.GET.get('name', '').strip()  # Ensures it's a string
    query_enrollment_date = request.GET.get('enrollment_date', '').strip()
    query_student_id = request.GET.get('student_id', '').strip()

    students = Student.objects.all()

    if query_name:
        students = students.filter(name__icontains=query_name)

    if query_enrollment_date:
        students = students.filter(enrollment__enrollment_date=query_enrollment_date)

    if query_student_id:
        students = students.filter(student_id__icontains=query_student_id)

    return render(request, 'student_list.html', {'students': students})

# View to add a new student
def student_add(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('student_list')
    else:
        form = StudentForm()
    return render(request, 'student_form.html', {'form': form})

# View to edit an existing student
def student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            return redirect('student_list')
    else:
        form = StudentForm(instance=student)
    return render(request, 'student_form.html', {'form': form})

# View to delete a student
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        student.delete()
        return redirect('student_list')
    return render(request, 'student_confirm_delete.html', {'student': student})

# View to display the list of enrollments
def enrollment_list(request):
    query_name = request.GET.get('name', '').strip()
    query_enrollment_date = request.GET.get('enrollment_date', '').strip()
    query_student_id = request.GET.get('student_id', '').strip()

    enrollments = Enrollment.objects.all()

    if query_name:
        enrollments = enrollments.filter(student__name__icontains=query_name)

    if query_enrollment_date:
        enrollments = enrollments.filter(enrollment_date=query_enrollment_date)

    if query_student_id:
        enrollments = enrollments.filter(student__student_id__icontains=query_student_id)

    return render(request, 'enrollment_list.html', {'enrollments': enrollments})

# View to add a new enrollment
def enrollment_add(request):
    if request.method == 'POST':
        form = EnrollmentForm(request.POST)
        if form.is_valid():
            enrollment = form.save(commit=False)
            try:
                enrollment.save()
                return redirect('enrollment_list')
            except ValidationError as e:
                return render(request, 'enrollment_full.html', {'error_message': str(e)})
    else:
        form = EnrollmentForm()
    return render(request, 'enrollment_form.html', {'form': form})

# View to edit an existing enrollment
def enrollment_edit(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    if request.method == 'POST':
        form = EnrollmentForm(request.POST, instance=enrollment)
        student_id = request.POST.get('student')
        if form.is_valid() and student_id:
            student = get_object_or_404(Student, id=student_id)
            enrollment = form.save(commit=False)
            enrollment.student = student
            enrollment.save()
            return redirect('enrollment_list')
    else:
        form = EnrollmentForm(instance=enrollment)
    return render(request, 'enrollment_form.html', {'form': form})

# View to delete an enrollment
def enrollment_delete(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    if request.method == 'POST':
        enrollment.delete()
        return redirect('enrollment_list')
    return render(request, 'enrollment_confirm_delete.html', {'enrollment': enrollment})

# View to get available slots for a course
def get_slots(request):
    course_id = request.GET.get('course_id')
    slots = Slot.objects.filter(course_id=course_id).order_by('start_time')
    slots_data = [{
        'id': slot.id, 
        'start_time': slot.start_time, 
        'end_time': slot.end_time,
        'instructor': slot.instructor if slot.instructor else "Not Assigned"
    } for slot in slots]
    return JsonResponse({'slots': slots_data})


# View to display the list of courses
def course_list(request):
    courses = Course.objects.all()
    return render(request, 'course_list.html', {'courses': courses})

# View to add a new course
def course_add(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('course_list')
    else:
        form = CourseForm()
    return render(request, 'course_form.html', {'form': form})

# View to edit an existing course
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            return redirect('course_list')
    else:
        form = CourseForm(instance=course)
    return render(request, 'course_form.html', {'form': form})

# View to delete a course
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        course.delete()
        return redirect('course_list')
    return render(request, 'course_confirm_delete.html', {'course': course})

# View to display the list of slots
def slot_list(request):
    slots = Slot.objects.all()
    slot_data = []
    for slot in slots:
        if slot.course.requires_lab and slot.lab:
            total_students_in_lab = Slot.objects.filter(lab=slot.lab, start_time=slot.start_time, end_time=slot.end_time).aggregate(total=models.Sum('current_students'))['total'] or 0
            available_seats = slot.lab.capacity - total_students_in_lab
        else:
            available_seats = slot.max_students - slot.current_students
        slot_data.append({'slot': slot, 'available_seats': available_seats})
    return render(request, 'slot_list.html', {'slot_data': slot_data})

# View to add a new slot
def slot_add(request):
    if request.method == 'POST':
        form = SlotForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('slot_list')
    else:
        form = SlotForm()
    return render(request, 'slot_form.html', {'form': form})

# View to edit an existing slot
def slot_edit(request, pk):
    slot = get_object_or_404(Slot, pk=pk)
    if request.method == 'POST':
        form = SlotForm(request.POST, instance=slot)
        if form.is_valid():
            form.save()
            return redirect('slot_list')
    else:
        form = SlotForm(instance=slot)
    return render(request, 'slot_form.html', {'form': form})

# View to delete a slot
def slot_delete(request, pk):
    slot = get_object_or_404(Slot, pk=pk)
    if request.method == 'POST':
        slot.delete()
        return redirect('slot_list')
    return render(request, 'slot_confirm_delete.html', {'slot': slot})

# View to display the list of fees
def fee_list(request):
    today = date.today()
    first_day_of_month = today.replace(day=1)
    query_name = request.GET.get('name')
    query_student_id = request.GET.get('student_id')
    query_enrollment_date = request.GET.get('enrollment_date')
    fees = Fee.objects.filter(due_date__gte=first_day_of_month, due_date__lte=today)
    if query_name:
        fees = fees.filter(enrollment__student__name__icontains = query_name)
    if query_student_id:
        fees = fees.filter(enrollment__student__student_id__icontains = query_student_id)
    if query_enrollment_date:
        fees = fees.filter(enrollment__enrollment_date=query_enrollment_date)
    return render(request, 'fee_list.html', {'fees': fees})

# View to add a new fee
def fee_add(request):
    if request.method == 'POST':
        form = FeeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('fee_list')
    else:
        form = FeeForm()
    return render(request, 'fee_form.html', {'form': form})

# View to edit an existing fee
def fee_edit(request, pk):
    fee = get_object_or_404(Fee, pk=pk)
    if request.method == 'POST':
        form = FeeForm(request.POST, instance=fee)
        if form.is_valid():
            form.save()
            return redirect('fee_list')
    else:
        form = FeeForm(instance=fee)
    return render(request, 'fee_form.html', {'form': form})

# View to delete a fee
def fee_delete(request, pk):
    fee = get_object_or_404(Fee, pk=pk)
    if request.method == 'POST':
        fee.delete()
        return redirect('fee_list')
    return render(request, 'fee_confirm_delete.html', {'fee': fee})

# View to display the overdue fees report
def overdue_fees_report(request):
    today = date.today()
    due_enrollments = Enrollment.objects.filter(fee__due_date__lt=today, fee__is_paid=False).distinct()
    return render(request, 'overdue_fees_report.html', {'due_enrollments': due_enrollments})

# View to display details of a student
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    return render(request, 'student_detail.html', {'student': student})

# View to search for students
def search_students(request):
    query = request.GET.get('q', '')
    students = Student.objects.filter(Q(name__icontains=query) | Q(student_id__icontains=query))
    student_list = [{'id': student.id, 'name': student.name, 'student_id': student.student_id} for student in students]
    return JsonResponse({'students': student_list})

# View to display the list of attendance records
def attendance_list(request):
    slot_name = request.GET.get('slot_name', '')
    instructor_name = request.GET.get('instructor_name', '')
    date_str = request.GET.get('date', '')

    slots = Slot.objects.all()

    if slot_name:
        slots = slots.filter(course__name__icontains=slot_name)
    if instructor_name:
        slots = slots.filter(instructor__icontains=instructor_name)

    selected_slot_id = request.GET.get('slot_id')
    attendance_records = []
    selected_date = date.today()
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect('attendance_list')

    if request.method == 'POST' and selected_slot_id:
        selected_slot = get_object_or_404(Slot, id=selected_slot_id)
        for enrollment in Enrollment.objects.filter(slot=selected_slot):
            status = request.POST.get(f'status_{enrollment.id}')
            Attendance.objects.update_or_create(
                enrollment=enrollment,
                date=selected_date,
                defaults={'status': status}
            )
        messages.success(request, "Attendance marked successfully!")
        return redirect('attendance_list')

    if selected_slot_id:
        selected_slot = get_object_or_404(Slot, id=selected_slot_id)
        enrollments = Enrollment.objects.filter(slot=selected_slot)
        for enrollment in enrollments:
            attendance_record = Attendance.objects.filter(enrollment=enrollment, date=selected_date).first()
            attendance_records.append({
                'enrollment': enrollment,
                'status': attendance_record.status if attendance_record else None,
                'attendance_marked': attendance_record is not None,
            })

    context = {
        'slots': slots,
        'attendance_records': attendance_records,
        'selected_slot_id': selected_slot_id,
        'selected_date': selected_date.strftime('%Y-%m-%d'),
    }
    return render(request, 'attendance.html', context)

# View to display the list of enrolled students for a slot
def view_enrolled_students(request, slot_id):
    slot = get_object_or_404(Slot, id=slot_id)
    enrollments = Enrollment.objects.filter(slot=slot).select_related('student')
    context = {
        'slot': slot,
        'enrollments': enrollments,
    }
    return render(request, 'view_enrolled_students.html', context)