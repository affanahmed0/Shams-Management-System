from django.core.management.base import BaseCommand
from student_management.models import Enrollment

class Command(BaseCommand):
    help = 'Remove finished enrollments and move students to FinalTest model'

    def handle(self, *args, **kwargs):
        Enrollment.remove_finished_enrollments()
        self.stdout.write(self.style.SUCCESS('Successfully removed finished enrollments and moved students to FinalTest model'))