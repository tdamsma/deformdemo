# -*- coding: utf-8 -*-

""" A Pyramid app that demonstrates various Deform widgets and
capabilities and which provides a functional test suite  """

import csv
import decimal
import inspect
import logging
import pprint
import random
import sys

import colander
from pyramid.config import Configurator
from pyramid.i18n import TranslationStringFactory
from pyramid.i18n import get_locale_name
from pyramid.i18n import get_localizer
from pyramid.renderers import get_renderer
from pyramid.response import Response
from pyramid.session import UnencryptedCookieSessionFactoryConfig
from pyramid.threadlocal import get_current_request
from pyramid.view import view_config
from pyramid.view import view_defaults

import deform
from deform.renderer import configure_zpt_renderer
from iso8601 import iso8601
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer

from .extra_widgets import (
    DateTimeNativeWidget,
    JExcelObjectArrayWidget,
    ReactJsonSchemaFormWidget,
    resource_registry,
    Select2JsonWidget,
    Select2JsonWidget,
    Select2SortableWidget,
)
import jsonschema as JsonSchema

log = logging.getLogger(__name__)

from pkg_resources import resource_filename

deform_templates = resource_filename("deform", "templates")
extra_templates = resource_filename("deformdemo", "templates")
search_path = (
    deform_templates,
    extra_templates,
)
deform.Form.set_zpt_renderer(search_path)

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


PY3 = sys.version_info[0] == 3
PY38MIN = sys.version_info[0] == 3 and sys.version_info[1] >= 8

if PY3:

    def unicode(val, encoding="utf-8"):
        return val


_ = TranslationStringFactory("deformdemo")

formatter = HtmlFormatter(nowrap=True)
css = formatter.get_style_defs()

# the zpt_renderer above is referred to within the demo.ini file by dotted name


class demonstrate(object):
    def __init__(self, title):
        self.title = title

    def __call__(self, method):
        method.demo = self.title
        return method


# Py2/Py3 compat
# http://stackoverflow.com/a/16888673/315168
# eliminate u''
def my_safe_repr(obj, context, maxlevels, level, sort_dicts=True):

    if type(obj) == unicode:
        obj = obj.encode("utf-8")

    # Python 3.8 changed the call signature of pprint._safe_repr.
    # by adding sort_dicts.
    if PY38MIN:
        return pprint._safe_repr(obj, context, maxlevels, level, sort_dicts)
    else:
        return pprint._safe_repr(obj, context, maxlevels, level)


@view_defaults(route_name="deformdemo")
class DeformDemo(object):
    def __init__(self, request):
        self.request = request
        self.macros = get_renderer("templates/main.pt").implementation().macros

    def render_form(
        self,
        form,
        appstruct=colander.null,
        submitted="submit",
        success=None,
        readonly=False,
        is_i18n=False,
    ):

        captured = None

        if submitted in self.request.POST:
            # the request represents a form submission
            try:
                # try to validate the submitted values
                controls = self.request.POST.items()
                captured = form.validate(controls)
                if success:
                    response = success()
                    if response is not None:
                        return response
                html = form.render(captured)
            except deform.ValidationFailure as e:
                # the submitted values could not be validated
                html = e.render()

        else:
            # the request requires a simple form rendering
            html = form.render(appstruct, readonly=readonly)

        if self.request.is_xhr:
            return Response(html)

        code, start, end = self.get_code(2)
        locale_name = get_locale_name(self.request)

        reqts = form.get_widget_resources()

        printer = pprint.PrettyPrinter()
        printer.format = my_safe_repr
        output = printer.pformat(captured)
        captured = highlight(output, PythonLexer(), formatter)

        # values passed to template for rendering
        return {
            "form": html,
            "captured": captured,
            "code": code,
            "start": start,
            "end": end,
            "is_i18n": is_i18n,
            "locale": locale_name,
            "demos": self.get_demos(),
            "title": self.get_title(),
            "css_links": reqts["css"],
            "js_links": reqts["js"],
        }

    def get_code(self, level):
        frame = sys._getframe(level)
        lines, start = inspect.getsourcelines(frame.f_code)
        end = start + len(lines)
        code = "".join(lines)
        if not PY3:
            code = unicode(code, "utf-8")
        return highlight(code, PythonLexer(), formatter), start, end

    @view_config(name="thanks.html")
    def thanks(self):
        return Response(
            "<html><body><p>Thanks!</p><small>"
            '<a href="..">Up</a></small></body></html>'
        )

    @view_config(name="allcode", renderer="templates/code.pt")
    def allcode(self):
        params = self.request.params
        start = params.get("start")
        end = params.get("end")
        hl_lines = None
        if start and end:
            start = int(start)
            end = int(end)
            hl_lines = list(range(start, end))
        code = open(inspect.getsourcefile(self.__class__), "r").read()
        code = code.encode("utf-8")
        formatter = HtmlFormatter(
            linenos="table",
            lineanchors="line",
            cssclass="hightlight ",
            hl_lines=hl_lines,
        )
        html = highlight(code, PythonLexer(), formatter)
        return {"code": html, "demos": self.get_demos()}

    def get_title(self):
        # gross hack; avert your eyes
        frame = sys._getframe(3)
        attr = frame.f_locals["attr"]
        inst = frame.f_locals["inst"]
        method = getattr(inst, attr)
        return method.demo

    @view_config(name="pygments.css")
    def cssview(self):
        response = Response(body=css, content_type="text/css")
        response.cache_expires = 360
        return response

    @view_config(renderer="templates/index.pt")
    def index(self):
        return {"demos": self.get_demos()}

    def get_demos(self):
        def predicate(value):
            if getattr(value, "demo", None) is not None:
                return True

        demos = inspect.getmembers(self, predicate)
        L = []
        for name, method in demos:
            url = self.request.resource_url(
                self.request.root, name, route_name="deformdemo"
            )
            L.append((method.demo, url))
        L.sort()
        return L

    @view_config(renderer="templates/form.pt", name="select2sortable")
    @demonstrate("Select2Sortable Widget")
    def select2sortable(self):

        choices = (
            ("", "- Select -"),
            ("habanero", "Habanero"),
            ("jalapeno", "Jalapeno"),
            ("chipotle", "Chipotle"),
        )

        class Schema(colander.Schema):
            pepper = colander.SchemaNode(
                colander.List(),
                widget=Select2SortableWidget(values=choices),
            )

        schema = Schema()
        form = deform.Form(
            schema,
            buttons=("submit",),
            resource_registry=resource_registry,
        )

        return self.render_form(form)

    @view_config(renderer="templates/form.pt", name="select2json")
    @demonstrate("Select2Json Widget")
    def select2json(self):

        choices = (
            ("", "- Select -"),
            ({"a": 1}, "a=1"),
            ({"b": 2}, "b=2"),
            ({"c": 1, "d": 5}, "c=1, d=5"),
        )

        class Schema(colander.Schema):
            pepper = colander.SchemaNode(
                colander.Mapping(unknown="preserve"),
                widget=Select2JsonWidget(values=choices),
            )

        schema = Schema()
        form = deform.Form(
            schema,
            buttons=("submit",),
            resource_registry=resource_registry,
        )

        return self.render_form(form)

    @view_config(renderer="templates/form.pt", name="reactjsonschemaform")
    @demonstrate("ReactJsonschemaForm Widget")
    def reactjsonschemaform(self):

        jsonschema = {
            "title": "A registration form",
            "description": "A simple form example.",
            "type": "object",
            "required": ["firstName", "lastName"],
            "properties": {
                "firstName": {
                    "type": "string",
                    "title": "First name",
                    "default": "Chuck",
                },
                "lastName": {"type": "string", "title": "Last name"},
                "telephone": {
                    "type": "string",
                    "title": "Telephone",
                    "minLength": 10,
                },
            },
        }

        class Schema(colander.Schema):

            registration = colander.SchemaNode(
                colander.Mapping(unknown="preserve"),
                widget=ReactJsonSchemaFormWidget(jsonschema=jsonschema),
            )

        def validator(form, value):
            try:
                JsonSchema.validate(value['data'], jsonschema)
            except JsonSchema.exceptions.ValidationError as exc:
                raise colander.Invalid(form, exc.message) from exc

        schema = Schema(validator=validator)
        schema = Schema()
        form = deform.Form(
            schema,
            buttons=("submit",),
            resource_registry=resource_registry,
        )

        return self.render_form(form)

    @view_config(renderer="templates/form.pt", name="reactjsonschemaform2")
    @demonstrate("ReactJsonschemaForm Widget (more complicated)")
    def reactjsonschemaform2(self):

        jsonschema = {
            "title": "Contextualized errors",
            "type": "object",
            "properties": {
                "firstName": {
                    "type": "string",
                    "title": "First name",
                    "minLength": 8,
                    "pattern": r"\d+",
                },
                "active": {"type": "boolean", "title": "Active"},
                "skills": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 5},
                },
                "multipleChoicesList": {
                    "type": "array",
                    "title": "Pick max two items",
                    "uniqueItems": True,
                    "maxItems": 2,
                    "items": {
                        "type": "string",
                        "enum": ["foo", "bar", "fuzz"],
                    },
                },
            },
        }

        class Schema(colander.Schema):
            data = colander.SchemaNode(
                colander.Mapping(unknown="preserve"),
                widget=ReactJsonSchemaFormWidget(jsonschema=jsonschema),
            )

        def validator(form, value):
            try:
                JsonSchema.validate(value['data'], jsonschema)
            except JsonSchema.exceptions.ValidationError as exc:
                raise colander.Invalid(form, exc.message) from exc

        schema = Schema(validator=validator)
        form = deform.Form(
            schema,
            buttons=("submit",),
            resource_registry=resource_registry,
        )

        return self.render_form(form)

    @view_config(renderer="templates/form.pt", name="datetime_native")
    @demonstrate("DateTime Native Widget ")
    def datetime_native(self):
        import datetime

        then = datetime.datetime(2011, 5, 5, 1, 2)

        class Schema(colander.Schema):
            date_time = colander.SchemaNode(
                colander.DateTime(),
                widget=DateTimeNativeWidget(),
            )

        schema = Schema()
        form = deform.Form(schema, buttons=("submit",))

        return self.render_form(form, appstruct={"date_time": then})

    @view_config(renderer="templates/form.pt", name="jexcel_objectarray")
    @demonstrate("JExcelObjectArray Widget")
    def jexcel_objectarray(self):
        class Row(colander.MappingSchema):
            first = colander.SchemaNode(colander.Integer())
            second = colander.SchemaNode(colander.String())

        class Rows(colander.SequenceSchema):
            row = Row()

        class Schema(colander.Schema):
            table = Rows(widget=JExcelObjectArrayWidget())

        schema = Schema()
        form = deform.Form(
            schema,
            buttons=("submit",),
            resource_registry=resource_registry,
        )

        return self.render_form(form)


class MemoryTmpStore(dict):
    """Instances of this class implement the
    :class:`deform.interfaces.FileUploadTempStore` interface"""

    def preview_url(self, uid):
        return None


tmpstore = MemoryTmpStore()


class SequenceToTextWidgetAdapter(object):
    def __init__(self, widget):
        self.widget = widget

    def __getattr__(self, name):
        return getattr(self.widget, name)

    def serialize(self, field, cstruct, readonly=False):
        if cstruct is colander.null:
            cstruct = []
        textrows = getattr(field, "unparseable", None)
        if textrows is None:
            outfile = StringIO()
            writer = csv.writer(outfile)
            writer.writerows(cstruct)
            textrows = outfile.getvalue()
        return self.widget.serialize(
            field, cstruct=textrows, readonly=readonly
        )

    def deserialize(self, field, pstruct):
        text = self.widget.deserialize(field, pstruct)
        if text is colander.null:
            return text
        if not text.strip():
            return colander.null
        try:
            infile = StringIO(text)
            reader = csv.reader(infile)
            rows = list(reader)
        except Exception as e:
            field.unparseable = pstruct
            raise colander.Invalid(field.schema, str(e))
        return rows

    def handle_error(self, field, error):
        msgs = []
        if error.msg:
            field.error = error
        else:
            for e in error.children:
                msgs.append("line %s: %s" % (e.pos + 1, e))
            field.error = colander.Invalid(field.schema, "\n".join(msgs))


def main(global_config, **settings):
    # paster serve entry point
    settings["debug_templates"] = "true"

    session_factory = UnencryptedCookieSessionFactoryConfig("seekrit!")
    config = Configurator(settings=settings, session_factory=session_factory)
    config.add_translation_dirs(
        "colander:locale", "deform:locale", "deformdemo:locale"
    )

    config.include("pyramid_chameleon")

    # Set up Chameleon templates (ZTP) rendering paths

    def translator(term):
        # i18n localizing function
        return get_localizer(get_current_request()).translate(term)

    # Configure renderer
    configure_zpt_renderer(("deformdemo:custom_widgets",), translator)

    config.add_static_view("static_deform", "deform:static")
    config.add_static_view("static", "static")
    config.add_route("deformdemo", "*traverse")

    def onerror(*arg):
        pass

    config.scan("deformdemo", onerror=onerror)
    return config.make_wsgi_app()
