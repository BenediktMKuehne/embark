# pylint: disable=W4903
__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Benedikt Kuehne, Maximilian Wagner, Mani Kumar, m-1-k-3, Ashutosh Singh, Garima Chauhan, diegiesskanne, VAISHNAVI UMESH, Vaish1795'
__license__ = 'MIT'

import builtins
import logging
import os
import shutil
import uuid
import re

from django.conf import settings
from django.db import models
from django import forms
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone

from porter.models import LogZipFile
from users.models import User as Userclass

logger = logging.getLogger(__name__)


def scan_modules_default_value():
    """
    emba modules to be executed
    """
    return {
        'scan_modules': []
    }


def jsonfield_default_value():
    """
    keys: percentage, analysis, firmwarename, last_update, last_module, module_list, last_phase, phase_list
    """
    return {
        "percentage": 0,
        'analysis': "",
        'firmware_name': "",
        'last_update': "",
        'last_module': "",
        'module_list': [],
        'last_phase': "",
        'phase_list': [],
        'finished': False,
        'work': False
    }


class BooleanFieldExpertModeForm(forms.BooleanField):
    """
    class BooleanFieldExpertModeForm
    Extension of forms.BooleanField to support expert_mode and readonly option for BooleanFields in Forms
    """
    def __init__(self, *args, **kwargs):
        self.expert_mode = kwargs.pop('expert_mode', True)
        self.readonly = kwargs.pop('readonly', False)
        # super(BooleanFieldExpertModeForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)


class BooleanFieldExpertMode(models.BooleanField):
    """
    class BooleanFieldExpertModeForm
    Extension of models.BooleanField to support expert_mode and readonly for BooleanFields option for Models
    """
    def __init__(self, *args, **kwargs):
        self.expert_mode = kwargs.pop('expert_mode', True)
        self.readonly = kwargs.pop('readonly', False)
        # super(BooleanFieldExpertMode, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class': BooleanFieldExpertModeForm, 'expert_mode': self.expert_mode, 'readonly': self.readonly}
        defaults.update(kwargs)
        return models.Field.formfield(self, **defaults)


class CharFieldExpertModeForm(forms.CharField):
    """
    class BooleanFieldExpertModeForm
    Extension of forms.CharField to support expert_mode and readonly for CharField option for Forms
    """
    def __init__(self, *args, **kwargs):
        self.expert_mode = kwargs.pop('expert_mode', True)
        self.readonly = kwargs.pop('readonly', False)
        # super(CharFieldExpertModeForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)


class TypedChoiceFieldExpertModeForm(forms.TypedChoiceField):
    """
    class TypedChoiceFieldExpertModeForm
    Extension of forms.TypedChoiceField to support expert_mode and readonly for TypedChoiceField option for Forms
    """
    def __init__(self, *args, **kwargs):
        self.expert_mode = kwargs.pop('expert_mode', True)
        self.readonly = kwargs.pop('readonly', False)
        # super(TypedChoiceFieldExpertModeForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)


class CharFieldExpertMode(models.CharField):
    """
    class CharFieldExpertMode
    Extension of models.BooleanField to support expert_mode and readonly for CharField option for Models
    """
    def __init__(self, *args, **kwargs):
        self.expert_mode = kwargs.pop('expert_mode', True)
        self.readonly = kwargs.pop('readonly', False)
        # super(CharFieldExpertMode, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class': CharFieldExpertModeForm, 'choices_form_class': TypedChoiceFieldExpertModeForm, 'expert_mode': self.expert_mode, 'readonly': self.readonly}
        defaults.update(kwargs)
        return models.Field.formfield(self, **defaults)


class FirmwareFile(models.Model):
    """
    class FirmwareFile
    Model to store zipped or bin firmware file and upload date
    """
    MAX_LENGTH = 127

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=True)

    is_archive = models.BooleanField(default=False, blank=True)
    upload_date = models.DateTimeField(default=timezone.now, blank=True)
    user = models.ForeignKey(Userclass, on_delete=models.SET_NULL, related_name='Fw_Upload_User', null=True, blank=True)

    def get_storage_path(self, filename):
        # file will be uploaded to MEDIA_ROOT/<id>/<filename>
        return os.path.join(f"{self.pk}", filename)

    file = models.FileField(upload_to=get_storage_path)

    def get_abs_path(self):
        return f"{settings.MEDIA_ROOT}/{self.pk}/{self.file.name}"

    def get_abs_folder_path(self):
        return f"{settings.MEDIA_ROOT}/{self.pk}"

    def __str__(self):
        return f"{self.file.name.replace('/', ' - ')}"  # this the only sanitizing we do?


@receiver(pre_delete, sender=FirmwareFile)
def delete_fw_pre_delete_post(sender, instance, **kwargs):
    """
    callback function
    delete the firmwarefile and folder structure in storage on recieve
    """
    if sender.file:
        shutil.rmtree(instance.get_abs_folder_path(), ignore_errors=False, onexc=logger.error("Error when trying to delete %s", instance.get_abs_folder_path()))
    else:
        logger.error("No related FW found for delete request: %s", str(sender))


class Vendor (models.Model):
    """
    class Vendor
    Model of vendor for devices
    (1 vendor --> n devices)
    """
    MAX_LENGTH = 127

    vendor_name = models.CharField(
        help_text='Vendor name', verbose_name="vendor name", max_length=MAX_LENGTH,
        blank=True, unique=True)

    class Meta:
        ordering = ['vendor_name']

    def __str__(self):
        return self.vendor_name


class Label (models.Model):
    """
    class Label
    Model for labels
    ( 1 device --> n labels )
    """
    MAX_LENGTH = 127

    label_name = models.CharField(
        help_text='label name', verbose_name="label name", max_length=MAX_LENGTH,
        blank=True, unique=True)
    label_date = models.DateTimeField(default=timezone.now, blank=True)

    class Meta:
        ordering = ['label_name']

    def __str__(self):
        return self.label_name


class Device(models.Model):
    """
    class Device
    Model of the device under test
    (m Devices <---> n FirmwareFiles)
    (m Device <----> p Analyses )
    * assumes device revisions as different devices etc.
    * case sensitive
    """
    MAX_LENGTH = 127

    device_name = models.CharField(help_text='Device name', verbose_name="Device name", max_length=MAX_LENGTH, blank=True)
    device_vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True)
    device_label = models.ForeignKey(Label, on_delete=models.SET_NULL, null=True, help_text='label/tag', related_query_name='label', editable=True, blank=True)   # TODO make many to many field
    device_date = models.DateTimeField(default=timezone.now, blank=True)
    device_user = models.ForeignKey(Userclass, on_delete=models.SET_NULL, related_name='Device_User', null=True)    # TODO change acces control to usergroup??

    visible = models.BooleanField(editable=True, default=True)

    class Meta:
        ordering = ['device_name']
        unique_together = ['device_name', 'device_vendor']

    def __str__(self):
        return f"{self.device_name}({self.device_vendor})"


class FirmwareAnalysis(models.Model):
    """
    class Firmware
    Model of firmware to be analyzed, basic/expert emba flags and metadata on the analyze process
    (1 FirmwareFile --> n FirmwareAnalysis)
    """
    MAX_LENGTH = 127

    # pk
    # id = HashidAutoField(primary_key=True, prefix='fwA_')
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=True)
    # user
    user = models.ForeignKey(Userclass, on_delete=models.SET_NULL, related_name='Fw_Analysis_User', null=True)
    # pid from within boundedexec
    pid = models.BigIntegerField(help_text='process id of subproc', verbose_name='PID', blank=True, null=True)

    firmware = models.ForeignKey(FirmwareFile, on_delete=models.SET_NULL, help_text='Firmware File object', null=True, editable=True, blank=True)
    firmware_name = models.CharField(editable=True, default="File unknown", max_length=MAX_LENGTH)

    # emba basic flags
    version = CharFieldExpertMode(
        help_text='Firmware version', verbose_name="Firmware version", max_length=MAX_LENGTH,
        blank=True, expert_mode=False)
    notes = CharFieldExpertMode(
        help_text='Testing notes', verbose_name="Testing notes", max_length=MAX_LENGTH,
        blank=True, expert_mode=False)

    # new hardware oriented tracking
    device = models.ManyToManyField(Device, help_text='device/platform', related_query_name='device', editable=True, max_length=MAX_LENGTH, blank=True)

    # emba expert flags
    firmware_Architecture = CharFieldExpertMode(
        choices=[
            (None, 'Select architecture'), ('MIPS', 'MIPS'), ('MIPS64R2', 'MIPS64R2'), ('MIPS64_III', 'MIPS64_III'), ('MIPS64_N32', 'MIPS64_N32'),
            ('ARM', 'ARM'), ('ARM64', 'ARM64'),
            ('x86', 'x86'), ('x64', 'x64'),
            ('PPC', 'PPC'), ('PPC64', 'PPC64'),
            ('NIOS2', 'NIOS2'), ('RISCV', 'RISCV'), ('QCOM_DSP6', 'QCOM_DSP6')
        ],
        verbose_name="Select architecture of the linux firmware",
        help_text='Architecture of the linux firmware [MIPS, ARM, x86, x64, PPC, NIOS2] -a will be added (note: other options are not in use yet)',
        max_length=MAX_LENGTH, blank=True, expert_mode=True
    )
    user_emulation_test = BooleanFieldExpertMode(help_text='Enables automated qemu emulation tests', default=False, expert_mode=True, blank=True)
    system_emulation_test = BooleanFieldExpertMode(help_text='Enables automated qemu system emulation tests', default=False, expert_mode=True, blank=True)

    # SBOM mode option
    sbom_only_test = models.BooleanField(verbose_name='SBOM only test', help_text='Enables SBOM default-profile', default=False, blank=True)

    # S-modules
    scan_modules = models.JSONField(blank=True, null=True, default=scan_modules_default_value)

    # TODO add -C and -k option

    # removed
    """
    dev_mode = BooleanFieldExpertMode(
        help_text='Run emba in developer mode, -D will be added ', default=False, expert_mode=True, blank=True)
    log_path = BooleanFieldExpertMode(
        help_text='Ignores log path check, -i will be added', default=False, expert_mode=True, blank=True)
    grep_able_log = BooleanFieldExpertMode(
        help_text='Create grep-able log file in [log_path]/fw_grep.log, -g will be added', default=True,
        expert_mode=True, blank=True)
    relative_paths = BooleanFieldExpertMode(
        help_text='Prints only relative paths, -s will be added', default=True, expert_mode=True, blank=True)
    ANSI_color = BooleanFieldExpertMode(
        help_text='Adds ANSI color codes to log, -z will be added', default=True, expert_mode=True, blank=True)
    web_reporter = BooleanFieldExpertMode(
        help_text='Activates web report creation in log path, -W will be added', default=True, expert_mode=True,
        blank=True)
    dependency_check = BooleanFieldExpertMode(
        help_text=' Checks dependencies but ignore errors, -F will be added', default=True, expert_mode=True,
        blank=True)
    multi_threaded = BooleanFieldExpertMode(
        help_text='Activate multi threading (destroys regular console output), -t will be added', default=True,
        expert_mode=True, blank=True)
    firmware_remove = BooleanFieldExpertMode(
        help_text='Remove extracted firmware file/directory after testint, -r will be added', default=True,
        expert_mode=True, blank=True)
    """
    # Zip file for porting and download
    zip_file = models.ForeignKey(LogZipFile, on_delete=models.SET_NULL, help_text='Archive file', null=True, editable=True, blank=True)

    # embark meta data
    path_to_logs = models.FilePathField(path=settings.EMBA_LOG_ROOT, editable=True, allow_folders=True)
    log_size = models.PositiveBigIntegerField(default=0, blank=True)
    start_date = models.DateTimeField(default=timezone.now, blank=True)
    end_date = models.DateTimeField(default=None, null=True)
    scan_time = models.DurationField(default=None, null=True)
    duration = models.CharField(blank=True, null=True, max_length=100, help_text='')
    finished = models.BooleanField(default=False, blank=False)
    failed = models.BooleanField(default=False, blank=False)

    # view option fields
    archived = models.BooleanField(default=False, blank=False)
    hidden = models.BooleanField(default=False, blank=False)

    # status/logreader-stuff
    status = models.JSONField(null=False, default=jsonfield_default_value)

    # additional Labels
    label = models.ManyToManyField(Label, help_text='tag/label', related_query_name='analysis-label', editable=True, max_length=MAX_LENGTH, blank=True)

    class Meta:
        app_label = 'uploader'

        """
        build shell command from input fields
        :params: None
        :return:
        """

    # def __init__(self, *args, **kwargs):
    #    super().__init__(*args, **kwargs)
    #    self.firmware_name = self.firmware.file.name

    def __str__(self):
        return f"{self.id}({self.firmware})"

    def get_flags(self):
        """
        build shell command from input fields

        :return: string formatted input flags for emba
        """

        command = ""
        if self.version:
            command = command + r" -X " + "\"" + re.sub(r"[^a-zA-Z0-9\.\-\_\+]+", "", str(self.version)) + "\""
        if self.device:
            devices = self.device.all()
            logger.debug("get_flags - device - to dict query returns %s", devices)
            _device_name_list = []
            _device_vendor_list = []
            for _device in devices:
                _device_name_list.append(_device.device_name)
                _device_vendor_list.append(_device.device_vendor.vendor_name)
            logger.debug("get_flags - device_name - to name dict %s", _device_name_list)
            logger.debug("get_flags - vendor_name - to name dict %s", _device_vendor_list)
            command = command + r" -Z " + "\"" + re.sub(r"[^a-zA-Z0-9\-\_]+", "", str(_device_name_list)) + "\""
            command = command + r" -Y " + "\"" + re.sub(r"[^a-zA-Z0-9\-\_]+", "", str(_device_vendor_list)) + "\""
        if self.notes:
            command = command + r" -N " + "\"" + re.sub(r"[^a-zA-Z0-9\.\-\_\ ]+", "", str(self.notes)) + f" (uuid:{self.id})" + "\""
        if self.firmware_Architecture:
            command = command + r" -a " + str(self.firmware_Architecture)
        if self.user_emulation_test:
            command = command + r" -E"
        if self.system_emulation_test:
            command = command + r" -Q"
        if self.scan_modules:
            for module_ in self.scan_modules:
                command = command + r" -m " + str(module_)
                if module_ == "s120":
                    command = command + r" -c "

        # running emba
        logger.info("final emba parameters %s", command)
        return command

    def do_archive(self):
        """
        cleans up the firmwareanalysis log_dir up to a point where it's minimal
        """
        logger.info("Archiving %s", self.id)
        needed_content_list = ["html_report", "SBOM", "csv_logs", "emba_error.log", "emba.log", "firmware_entropy.png", "json_logs", "pixd.png"]
        log_path = f"{self.path_to_logs}/emba_logs/"
        for _content in os.listdir(log_path):
            if _content not in needed_content_list and os.path.exists(os.path.join(log_path, _content)):
                shutil.rmtree(os.path.join(log_path, _content), ignore_errors=False, onerror=logger.error("Error when trying to delete %s", os.path.join(log_path, _content)))
        logger.debug("Reduced the size to. stat=%s", os.stat(log_path))
        logger.debug("Archived %s", self.id)


@receiver(pre_delete, sender=FirmwareAnalysis)
def delete_analysis_pre_delete(sender, instance, **kwargs):
    """
    callback function
    delete the analysis and folder structure in storage on recieve
    """
    # delete logs
    try:
        if sender.archived is False:
            if sender.path_to_logs != "/" and settings.EMBA_LOG_ROOT in sender.path_to_logs:
                shutil.rmtree(instance.path_to_logs, ignore_errors=False)
            logger.error("Can't delete log directory of: %s since it's %s", str(sender), instance.path_to_logs)
        elif sender.archived is True:
            # delete zip file
            sender.zip_file.delete()
        else:
            pass
    except builtins.Exception as _error:
        logger.error("Error durring delete of: %s - %s", str(sender), _error)


class ResourceTimestamp(models.Model):
    """
    class ResourceTimestamp
    Model to store zipped or bin firmware file and upload date
    """

    timestamp = models.DateTimeField(default=timezone.now)
    cpu_percentage = models.FloatField(default=0.0)
    memory_percentage = models.FloatField(default=0.0)
