from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Enrollment, FinalTest, Fee
from datetime import date, timedelta

@receiver(post_save, sender=Enrollment)
def remove_finished_enrollments(sender, instance, **kwargs):
    today = date.today()
    finished_enrollments = Enrollment.objects.filter(
        enrollment_date__lte=today - timedelta(days=30 * instance.course.duration_months)
    )
    for enrollment in finished_enrollments:
        FinalTest.objects.create(
            student=enrollment.student,
            course=enrollment.course,
            test_date=today
        )
        enrollment._skip_slot_update = True
        enrollment.delete()

@receiver(post_delete, sender=Enrollment)
def update_slot_current_students(sender, instance, **kwargs):
    if not hasattr(instance, '_skip_slot_update'):
        slot = instance.slot
        slot.current_students -= 1
        slot.save()

@receiver(post_save, sender=Fee)
def reset_fees_status(sender, instance, **kwargs):
    today = date.today()
    if today.day == 1:
        Fee.objects.update(is_paid=False)