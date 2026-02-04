from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import DrivingLicense, Passport, Vehicle, VehicleHandover


@receiver(post_save, sender=VehicleHandover)
def sync_vehicle_on_handover(sender, instance, **kwargs):
	"""Keep vehicle assignment in sync when a handover is saved."""
	if not instance.is_active:
		return

	# Mark all other handovers for this vehicle as inactive
	VehicleHandover.objects.filter(vehicle=instance.vehicle).exclude(id=instance.id).update(is_active=False)

	# Move the vehicle assignment to the new employee, if provided
	if instance.to_employee and instance.vehicle.employee_id != instance.to_employee_id:
		Vehicle.objects.filter(id=instance.vehicle_id).update(employee=instance.to_employee)


@receiver(post_save, sender=Passport)
def ensure_single_active_passport(sender, instance, **kwargs):
	"""Allow only one active passport per employee."""
	if not instance.is_active:
		return

	Passport.objects.filter(employee=instance.employee, is_active=True).exclude(id=instance.id).update(is_active=False)


@receiver(post_save, sender=DrivingLicense)
def ensure_single_active_license(sender, instance, **kwargs):
	"""Allow only one active driving license per employee."""
	if not instance.is_active:
		return

	DrivingLicense.objects.filter(employee=instance.employee, is_active=True).exclude(id=instance.id).update(is_active=False)

