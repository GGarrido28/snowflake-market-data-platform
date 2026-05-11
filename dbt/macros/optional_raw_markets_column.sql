{# Helpers used by stg_kalshi_markets to defensively project columns from RAW_MARKETS.
   Kalshi's market response shape varies by market type, so columns beyond the merge
   keys (ticker, event_ticker) may legitimately be absent. Each helper emits the typed
   column passthrough when the source column exists, or a typed NULL otherwise.

   Numeric helpers route through VARCHAR before try_to_decimal because Snowflake's
   TRY_CAST refuses FLOAT -> NUMBER directly; columns may land as FLOAT (newer scrapes)
   or VARCHAR (older scrapes) depending on the values SnowflakeManager sampled at
   CREATE TABLE time. Casting to VARCHAR first makes try_to_decimal work for both. #}

{% macro optional_string(column_set, col, alias) -%}
    {%- if col in column_set -%}
    "{{ col }}" as {{ alias }}
    {%- else -%}
    cast(null as varchar) as {{ alias }}
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
