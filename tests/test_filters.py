import datetime
from zoneinfo import ZoneInfo


from django.db.models import (
    Q,
    Value,
)
from django.test import (
    TestCase,
    override_settings,
)
from django.urls import (
    include,
    path,
)
from rest_framework.permissions import AllowAny
from rest_framework.routers import SimpleRouter
from rest_framework.serializers import ModelSerializer
from rest_framework.test import APIClient
from rest_framework.viewsets import ReadOnlyModelViewSet


from drf_query_filter import fields
from drf_query_filter.filters import QueryParamFilter


from .models import BasicModel


class BasicModelSerializer(ModelSerializer[BasicModel]):
    class Meta:
        model = BasicModel
        fields = "__all__"


class ModelViewSet(ReadOnlyModelViewSet[BasicModel]):
    queryset = BasicModel.objects.all().order_by("id")
    permission_classes = [AllowAny]
    serializer_class = BasicModelSerializer
    filter_backends = [QueryParamFilter]

    query_params = [
        fields.IntegerField("pk")
        & fields.ChoicesField("integer", choices=["10", "20", "30"]),
        fields.StringField(
            "search_startswith",
            ["string_uno__istartswith", "string_dos__istartswith"],
            connector=Q.OR,
        ),
        fields.StringField(
            "search_exact",
            ["string_uno", "string_dos"],
            connector=Q.OR,
        ),
        fields.ConcatField(
            "string_concat",
            ["string_uno", Value(" "), "string_dos"],
            lookup="icontains",
        ),
        fields.BooleanField("boolean") | fields.RangeDateField("date", equal=True),
    ]
    query_raise_exceptions = True


router = SimpleRouter()
router.register("test", ModelViewSet)

urlpatterns = [path("api/", include(router.urls))]


@override_settings(ROOT_URLCONF="tests.test_filters")
class FilterTests(TestCase):
    def test_filters(self) -> None:
        self.maxDiff = 999
        client = APIClient()
        dt = datetime.datetime(2026, 3, 10, 23, 0, 0, tzinfo=ZoneInfo("America/Phoenix"))
        instance_a = BasicModel.objects.create(
            string_uno="Roger",
            string_dos="Simon",
            date=dt.date(),
            integer=1,
            boolean=True,
        )
        dt = dt + datetime.timedelta(days=1)
        instance_b = BasicModel.objects.create(
            string_uno="blue",
            string_dos="red",
            date=dt.date(),
            integer=10,
            boolean=False,
        )
        dt = dt + datetime.timedelta(days=1)
        instance_c = BasicModel.objects.create(
            string_uno="Red",
            string_dos="Blue",
            date=dt.date(),
            integer=100,
            boolean=True,
        )
        dt = dt + datetime.timedelta(days=1)
        instance_d = BasicModel.objects.create(
            string_uno="XYC",
            string_dos="ABC",
            date=dt.date(),
            integer=100,
            boolean=True,
        )

        request = client.get("/api/test/", {"search_startswith": "R"}, format="json")
        self.assertEqual(request.status_code, 200)
        self.assertListEqual(
            [obj["id"] for obj in request.data],
            [instance_a.pk, instance_b.pk, instance_c.pk],
            "query: search=R",
        )

        request = client.get("/api/test/", {"search_exact": "Blue"}, format="json")
        self.assertEqual(request.status_code, 200)
        self.assertListEqual(
            [obj["id"] for obj in request.data],
            [instance_c.pk],
            "query: search_exact=Blue",
        )

        request = client.get("/api/test/", {"string_concat": "Blue"}, format="json")
        self.assertEqual(request.status_code, 200)
        self.assertListEqual(
            [obj["id"] for obj in request.data],
            [instance_b.pk, instance_c.pk],
            "query: search_concats=Blue",
        )

        request = client.get("/api/test/", {"integer": "3000"}, format="json")
        self.assertEqual(request.status_code, 400)
        self.assertIn("integer", request.data)
        self.assertEqual(request.data["integer"][0].code, "not_in_choices")

        request = client.get("/api/test/", {"integer": "10"}, format="json")
        self.assertEqual(request.status_code, 200)
        self.assertListEqual(
            [obj["id"] for obj in request.data],
            [instance_b.pk],
            "query: integer=10",
        )

        request = client.get("/api/test/", {"boolean": "1"}, format="json")
        self.assertEqual(request.status_code, 200)
        self.assertListEqual(
            [obj["id"] for obj in request.data],
            [instance_a.pk, instance_c.pk, instance_d.pk],
            "query: boolean=1",
        )

        request = client.get(
            "/api/test/",
            {"boolean": "0", "date": "2026-03-09,2026-03-10"},
            format="json",
        )
        self.assertEqual(request.status_code, 200)
        self.assertListEqual(
            [obj["id"] for obj in request.data],
            [instance_a.pk, instance_b.pk],
            "query: boolean=0, date=2025-03-09,2025-03-10",
        )
