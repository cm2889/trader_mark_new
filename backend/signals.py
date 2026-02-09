from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from .models import (
	DrivingLicense,
	Passport,
	Vehicle,
	VehicleHandover,
	UniformIssuance,
	UniformClearance,
	UniformStock,
	UniformStockTransactionLog,
)


def _create_stock_log(
	*,
	uniform_stock,
	transaction_type,
	quantity_change,
	quantity_before,
	quantity_after,
	created_by=None,
	issuance=None,
	clearance=None,
):
	UniformStockTransactionLog.objects.create(
		uniform_stock=uniform_stock,
		transaction_type=transaction_type,
		quantity_change=quantity_change,
		quantity_before=quantity_before,
		quantity_after=quantity_after,
		issuance=issuance,
		clearance=clearance,
		created_by=created_by,
	)


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


@receiver(pre_save, sender=UniformStock)
def track_previous_stock_quantity(sender, instance, **kwargs):
	"""Capture previous quantity for logging and adjustments."""
	if instance.pk:
		try:
			previous = UniformStock.objects.get(pk=instance.pk)
			instance._previous_quantity = previous.quantity
		except UniformStock.DoesNotExist:
			instance._previous_quantity = 0
	else:
		instance._previous_quantity = 0


@receiver(post_save, sender=UniformIssuance)
def update_stock_on_issuance(sender, instance, created, **kwargs):
	"""Decrease uniform stock quantity when a uniform is issued."""
	if created and instance.is_active:
		stock = instance.uniform_stock
		quantity_before = stock.quantity
		quantity_after = quantity_before - instance.quantity

		stock.quantity = quantity_after
		stock._transaction_context = {
			"transaction_type": "ISSUE",
			"quantity_change": -instance.quantity,
			"quantity_before": quantity_before,
			"quantity_after": quantity_after,
			"created_by": getattr(instance, "created_by", None),
			"issuance": instance,
			"clearance": None,
		}
		stock.save(update_fields=["quantity"])


@receiver(post_save, sender=UniformClearance)
def update_stock_on_clearance(sender, instance, created, **kwargs):
	"""Increase uniform stock quantity when a uniform is returned (cleared)."""
	if created and instance.is_active and instance.status == 'RETURNED':
		stock = instance.uniform_stock
		quantity_before = stock.quantity
		quantity_after = quantity_before + instance.quantity

		stock.quantity = quantity_after
		stock._transaction_context = {
			"transaction_type": "RETURN",
			"quantity_change": instance.quantity,
			"quantity_before": quantity_before,
			"quantity_after": quantity_after,
			"created_by": getattr(instance, "created_by", None),
			"issuance": None,
			"clearance": instance,
		}
		stock.save(update_fields=["quantity"])


@receiver(post_save, sender=UniformStock)
def log_uniform_stock_changes(sender, instance, created, **kwargs):
	"""Create transaction logs for stock changes, honoring contextual updates."""
	if not instance.is_active:
		return

	context = getattr(instance, "_transaction_context", None)
	if context:
		_create_stock_log(
			uniform_stock=instance,
			transaction_type=context["transaction_type"],
			quantity_change=context["quantity_change"],
			quantity_before=context["quantity_before"],
			quantity_after=context["quantity_after"],
			created_by=context.get("created_by"),
			issuance=context.get("issuance"),
			clearance=context.get("clearance"),
		)
		delattr(instance, "_transaction_context")
		return

	previous_quantity = getattr(instance, "_previous_quantity", None)
	if previous_quantity is None:
		return

	quantity_change = instance.quantity - previous_quantity
	if created:
		if instance.quantity == 0:
			return
		transaction_type = "ADD"
	elif quantity_change == 0:
		return
	else:
		transaction_type = "ADD" if quantity_change > 0 else "ADJUST"

	_create_stock_log(
		uniform_stock=instance,
		transaction_type=transaction_type,
		quantity_change=quantity_change,
		quantity_before=previous_quantity,
		quantity_after=instance.quantity,
		created_by=getattr(instance, "updated_by", None) or getattr(instance, "created_by", None),
	)

