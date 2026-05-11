{# Helpers for projecting a source column when it exists and a typed NULL when it
   doesn't. Useful when the upstream API/source response shape varies and the raw
   table is rebuilt by sampled-type inference (e.g. Kalshi markets, where new market
   types add/drop fields).

   Pass the column name and the lowercased list of available columns from the source.

   Numeric and timestamp helpers route the source column through VARCHAR before
   try_to_decimal / try_to_timestamp_ntz: Snowflake's TRY_CAST refuses FLOAT -> NUMBER
   directly, and columns may legitimately land as FLOAT (when all sampled values were
   floats) or VARCHAR (when string-typed). Casting to VARCHAR first makes the try_*
   functions work for both. #}

{% macro optional_string(column_set, col, alias) -%}
    {%- if col in column_set -%}
    "{{ col }}" as {{ alias }}
    {%- else -%}
    cast(null as varchar) as {{ alias }}
    {%- endif -%}
{%- endmacro %}

{% macro optional_boolean(column_set, col, alias) -%}
    {%- if col in column_set -%}
    "{{ col }}" as {{ alias }}
    {%- else -%}
    cast(null as boolean) as {{ alias }}
    {%- endif -%}
{%- endmacro %}

{% macro optional_integer(column_set, col, alias) -%}
    {%- if col in column_set -%}
    "{{ col }}" as {{ alias }}
    {%- else -%}
    cast(null as integer) as {{ alias }}
    {%- endif -%}
{%- endmacro %}

{% macro optional_decimal(column_set, col, alias, precision, scale) -%}
    {%- if col in column_set -%}
    try_to_decimal(cast("{{ col }}" as varchar), {{ precision }}, {{ scale }}) as {{ alias }}
    {%- else -%}
    cast(null as number({{ precision }}, {{ scale }})) as {{ alias }}
    {%- endif -%}
{%- endmacro %}

{% macro optional_timestamp(column_set, col, alias) -%}
    {%- if col in column_set -%}
    try_to_timestamp_ntz(cast("{{ col }}" as varchar)) as {{ alias }}
    {%- else -%}
    cast(null as timestamp_ntz) as {{ alias }}
    {%- endif -%}
{%- endmacro %}
