import uuid
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    """
    Extends default Django User with interview platform preferences and UUID.
    Provides IDOR protection and user-specific baseline preferences.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    target_role = models.CharField(max_length=120, blank=True, default='Software Engineer')
    years_of_experience = models.PositiveIntegerField(default=1)
    preferred_domain = models.CharField(max_length=60, blank=True, default='Full-Stack')
    anxiety_mode_default = models.BooleanField(
        default=False, 
        help_text="If enabled, practice mode defaults to un-scored, pressure-free session."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        indexes = [
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"Profile of {self.user.username} ({self.target_role})"


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    """Automatically maintain a UserProfile for every Django User instance."""
    if created:
        UserProfile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
