"""
Custom Django widget that integrates the Nepali date picker
(@anuz-pandey/nepali-date-picker) for date input fields.

The widget renders a text input with the 'nepali-date-picker' class,
which the JS library will auto-initialize. A hidden input stores the
AD date for Django form submission, while the visible input shows the BS date.
"""
from django import forms
from django.utils.safestring import mark_safe
import nepali_datetime


class NepaliDatePickerWidget(forms.DateInput):
    """
    Date picker widget that shows a Nepali BS calendar.
    The visible field shows the BS date; a hidden field stores the AD date.
    """

    class Media:
        css = {
            'all': (
                'https://cdn.jsdelivr.net/npm/@anuz-pandey/nepali-date-picker/dist/nepali-date-picker.min.css',
            )
        }
        js = (
            'https://cdn.jsdelivr.net/npm/@anuz-pandey/nepali-date-picker/dist/nepali-date-picker.min.js',
        )

    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}

        # Convert existing AD value to BS for display
        bs_display = ''
        ad_value = ''
        if value:
            if isinstance(value, str):
                # Try parsing if it's a string
                from datetime import datetime as dt
                try:
                    value = dt.strptime(value, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass

            if hasattr(value, 'year'):
                ad_value = value.strftime('%Y-%m-%d')
                try:
                    bs = nepali_datetime.date.from_datetime_date(value)
                    bs_display = bs.strftime('%Y-%m-%d')
                except (ValueError, OverflowError):
                    bs_display = ad_value

        hidden_id = f'id_{name}'
        visible_id = f'id_{name}_nepali'

        html = f'''
        <input type="hidden" name="{name}" id="{hidden_id}" value="{ad_value}">
        <input type="text" id="{visible_id}" value="{bs_display}"
               class="vDateField nepali-date-picker-field"
               style="padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px; width: 220px;"
               placeholder="Select Nepali Date" autocomplete="off" readonly>
        <script>
        (function() {{
            function initNepaliPicker() {{
                if (typeof NepaliDatePicker === 'undefined') {{
                    setTimeout(initNepaliPicker, 100);
                    return;
                }}
                var picker = new NepaliDatePicker('#{visible_id}', {{
                    ndpYear: true,
                    ndpMonth: true,
                    ndpYearCount: 20,
                    onChange: function(data) {{
                        // data contains: bsDate, adDate, bsMonth, bsYear, bsDay
                        document.getElementById('{hidden_id}').value = data.adDate;
                    }}
                }});
            }}
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', initNepaliPicker);
            }} else {{
                initNepaliPicker();
            }}
        }})();
        </script>
        '''
        return mark_safe(html)
