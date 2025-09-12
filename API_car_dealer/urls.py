from rest_framework.authtoken.views import obtain_auth_token
from django.contrib import admin
from django.urls import path, re_path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf.urls.static import static
from django.conf import settings

schema_view = get_schema_view(
   openapi.Info(
      title="Car Dealer API",
      default_version='v1',
      description="API for buying and selling cars.",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@example.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    
    # Роуты API
    path('api/v1/', include('core.api_urls')),
    
    # Swagger UI
    re_path(r'^swagger\.json$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)