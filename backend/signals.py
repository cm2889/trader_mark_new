from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from .models import DrivingLicense, Passport, Vehicle, VehicleHandover, UniformIssuance, UniformClearance, UniformStock


@receiver(post_save, sender=VehicleHandover)
def sync_vehicle_on_handover(sender, instance, **kwargs):
	"""Keep vehicle assignment in sync when a handover is saved."""
	if not instance.is_active:
		return

	# Mark all other handovers for this vehicle as inactive
	VehicleHandover.objects.filter(vehicle=instance.vehicle).exclude(id=instance.id).update(is_active=False)


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


@receiver(pre_save, sender=UniformIssuance)
def check_stock_before_issuance(sender, instance, **kwargs):
	"""Check if there is enough stock before issuing uniform."""
	if not instance.pk:  # Only for new issuances
		stock = instance.uniform_stock
		if stock.quantity < instance.quantity:
			raise ValidationError(
				f"Insufficient stock! Available: {stock.quantity}, Requested: {instance.quantity}"
			)


@receiver(post_save, sender=UniformIssuance)
def update_stock_on_issuance(sender, instance, created, **kwargs):
	"""Decrease uniform stock quantity when a uniform is issued."""
	if created and instance.is_active:
		stock = instance.uniform_stock
		stock.quantity -= instance.quantity
		stock.save()


@receiver(post_save, sender=UniformClearance)
def update_stock_on_clearance(sender, instance, created, **kwargs):
	"""Increase uniform stock quantity when a uniform is returned (cleared)."""
	if created and instance.is_active and instance.status == 'RETURNED':
		stock = instance.uniform_stock
		stock.quantity += instance.quantity
		stock.save()

