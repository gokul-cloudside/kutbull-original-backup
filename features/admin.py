from django.contrib import admin
from .models import Feature, FeatureCategory, DGClientSubscription, RoleAccess, \
    DataglenClient, Dashboard, SubscriptionPlan

# Register subscription.
class DataGlenSubscriptionAdmin(admin.ModelAdmin):
    model = SubscriptionPlan

admin.site.register(SubscriptionPlan, DataGlenSubscriptionAdmin)


class FeatureCategoryInline(admin.TabularInline):
    model = Feature


class DGFeatureCategoryAdmin(admin.ModelAdmin):
    model = FeatureCategory
    inlines = [FeatureCategoryInline]

admin.site.register(FeatureCategory, DGFeatureCategoryAdmin)

admin.site.register(Feature)

admin.site.register(DGClientSubscription)

admin.site.register(RoleAccess)