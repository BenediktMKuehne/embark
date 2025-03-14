__copyright__ = 'Copyright 2022-2025 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

import logging

from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponseBadRequest
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import MultipleObjectsReturned

from django_tables2 import RequestConfig

from dashboard.models import Result, SoftwareBillOfMaterial
from embark.helper import rnd_rgb_color, rnd_rgb_full
from uploader.forms import DeviceForm, LabelForm, VendorForm
from uploader.models import FirmwareAnalysis, Device, Vendor
from tracker.tables import SimpleDeviceTable, SimpleResultTable, SimpleSBOMTable
from tracker.forms import AssociateForm, TimeForm

logger = logging.getLogger(__name__)
req_logger = logging.getLogger("requests")


@permission_required("users.tracker_permission", login_url='/')
@require_http_methods(["GET", "POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def tracker(request):
    if request.method == 'POST':
        form = TimeForm(request.POST)
        if form.is_valid():
            logger.debug("Posted Form is valid")
            date = form.cleaned_data['date']
            queryset = Vendor.objects.all()
            if queryset.count() != 0:
                label_list = []
                data = []
                for _vendor in queryset:
                    label_list.append(_vendor.vendor_name)
                    data.append(Device.objects.filter(device_vendor=_vendor, device_date__gte=date).count())  # TODO better intervall?
                device_table = SimpleDeviceTable(data=Device.objects.all(), template_name="django_tables2/bootstrap-responsive.html")
                RequestConfig(request).configure(device_table)
                time_form = TimeForm()
                return render(request=request, template_name='tracker/index.html', context={'username': request.user.username, 'table': device_table, 'labels': label_list, 'data': data, 'time_form': time_form})
            logger.info("no data for the tracker yet %s", request)
            messages.error(request, 'No Device data to track')
            return redirect('embark-uploader-home')
        logger.error("invalid date form")
        return redirect('..')
    date = timezone.localdate() - timezone.timedelta(days=7)
    vendor_list = Vendor.objects.all()
    if vendor_list.count() == 0:
        logger.info("no data for the tracker yet - %s", request)
        messages.error(request, "no data for the tracker yet")
    label_list = []
    data = []
    color_list = []
    border_list = []
    for _vendor in vendor_list:
        label_list.append(_vendor.vendor_name)
        _device_count = Device.objects.filter(device_vendor=_vendor, device_date__gte=date).count()
        logger.debug("device count in tracker is : %d", _device_count)
        data.append(_device_count)
        color_list.append(rnd_rgb_full())
        border_list.append(rnd_rgb_color())
    device_table = SimpleDeviceTable(data=Device.objects.filter(device_date__gte=date), template_name="django_tables2/bootstrap-responsive.html")
    RequestConfig(request).configure(device_table)
    time_form = TimeForm()
    device_form = DeviceForm()
    label_form = LabelForm()
    vendor_form = VendorForm()
    logger.debug("device data : %s , %s, %s", data, color_list, border_list)
    return render(request=request, template_name='tracker/index.html', context={
        'username': request.user.username,
        'table': device_table,
        'labels': label_list,
        'data': data,
        'colors': color_list,
        'borders': border_list,
        'time_form': time_form,
        'device_form': device_form,
        'vendor_form': vendor_form,
        'label_form': label_form
        }
    )


@permission_required("users.tracker_permission", login_url='/')
@require_http_methods(["GET", "POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def get_report_for_device(request, device_id):
    if Device.objects.filter(id=device_id).exists():
        device = Device.objects.get(id=device_id)
        analysis_queryset = FirmwareAnalysis.objects.filter(device=device, failed=False)  # TODO uhm Q working? and add user check
        label_list = [
            'strcpy',
            'cve_high',
            'cve_medium',
            'cve_low',
            'exploits'
        ]
        data = []
        if not analysis_queryset:
            # FIXME
            messages.error(request, "there seems to be only failed analysis for this device")
            logger.debug("No firmware analysis available for this device")
            return redirect('embark-tracker')
        for _analysis in analysis_queryset:
            dataset = {}
            dataset['label'] = str(_analysis.version)
            result_queryset = Result.objects.filter(firmware_analysis=_analysis)
            logger.debug("result object: %s", result_queryset)
            try:
                if not result_queryset:
                    logger.error("result empty for %s", str(_analysis.id))
                    dataset['data'] = [0, 0, 0, 0, 0]
                else:
                    result_obj = result_queryset.first()  # should only be one obj
                    data_list = []
                    for _label in label_list:
                        data_list.append(getattr(result_obj, _label))
                    dataset['data'] = data_list
                    logger.debug("result data: %s", dataset['data'])
            except BaseException as excep:
                logger.error("result empty for %s", str(_analysis.id))
                dataset['data'] = [0, 0, 0, 0, 0]
                logger.error("ERROR: %s", excep)
            dataset['fill'] = "true"
            dataset['backgroundColor'] = rnd_rgb_full()
            dataset['borderColor'] = rnd_rgb_color()
            dataset['pointBackgroundColor'] = rnd_rgb_color()
            dataset['pointBorderColor'] = '#fff'
            dataset['pointHoverBackgroundColor'] = '#fff'
            dataset['pointHoverBorderColor'] = rnd_rgb_color()
            data.append(dataset)

        result_queryset = Result.objects.filter(firmware_analysis__in=analysis_queryset)
        if result_queryset:
            result_table = SimpleResultTable(data=result_queryset.all(), template_name="django_tables2/bootstrap-responsive.html")
            RequestConfig(request).configure(result_table)
        logger.debug("tracker/device data: %s", str(data))
        return render(request=request, template_name='tracker/device.html', context={'username': request.user.username, 'device_id': device_id, 'device': device, 'labels': label_list, 'data': data, 'result_table': result_table})
    logger.error("device id nonexistent: %s", device_id)
    logger.error("could  not get template - %s", request)
    return HttpResponseBadRequest("Bad Request")


@permission_required("users.tracker_permission", login_url='/')
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def get_sbom(request, sbom_id):
    req_logger.info("REquest from %s : %s", request.user, request)
    try:
        sbom_obj = SoftwareBillOfMaterial.objects.get(id=sbom_id)
        sbom_table = SimpleSBOMTable(data=sbom_obj.component.all(), template_name="django_tables2/bootstrap-responsive.html")
        logger.debug("Look at this sbom table!: %s", sbom_table)
        RequestConfig(request).configure(sbom_table)
    except MultipleObjectsReturned as multi_error:
        messages.error(request, "wrong number of result objects %s ", multi_error)
        sbom_table = None
    logger.debug("Rendering sbom.html")
    return render(request, "tracker/sbom.html", {'sbom_table': sbom_table})


@permission_required("users.tracker_permission", login_url='/')
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def tracker_time(request, time):
    queryset = Vendor.objects.filter(vendor_date__gte=time)
    if queryset.count() != 0:
        label_list = []
        data = []
        for _vendor in queryset:
            label_list.append(_vendor.vendor_name)
            data.append(Device.objects.filter(device_vendor=_vendor).count())
        device_table = SimpleDeviceTable(data=Device.objects.all(), template_name="django_tables2/bootstrap-responsive.html")
        return render(request=request, template_name='tracker/index.html', context={'username': request.user.username, 'table': device_table, 'labels': label_list, 'data': data})
    return HttpResponseBadRequest("Bad Request")


@permission_required("users.tracker_permission", login_url='/')
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def set_associate_device_to(request, analysis_id):
    if request.method == 'POST':
        form = AssociateForm(request.POST)
        if form.is_valid():
            logger.debug("Posted Form is valid")
            device = form.cleaned_data['device']
            analysis = FirmwareAnalysis.objects.get(id=analysis_id)
            analysis.device.add(device)
            messages.info(request, "Send request for association")
    return redirect('embark-tracker')


@permission_required("users.tracker_permission", login_url='/')
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def toggle_device_visible(request, device_id):
    device = Device.objects.get(id=device_id)
    if request.user != device.device_user:
        logger.error("User %s - access denied", request.user.username)
        messages.error(request, 'Access denied not the owner')
        return redirect('.')
    device.visible = not device.visible
    device.save()
    messages.info(request, 'Success')
    return redirect('.')
