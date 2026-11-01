--
-- PostgreSQL database dump
--

\restrict RhF3JcfGH8QXfyBc2JEzCCH0HmO50UER3ycvCiav3YYmU1R7IBRNo5iXBkZh9ny

-- Dumped from database version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: wind_direction; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.wind_direction AS ENUM (
    'N',
    'NNE',
    'NE',
    'ENE',
    'E',
    'ESE',
    'SE',
    'SSE',
    'S',
    'SSW',
    'SW',
    'WSW',
    'W',
    'WNW',
    'NW',
    'NNW'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: air_quality; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.air_quality (
    id integer NOT NULL,
    observation_id integer NOT NULL,
    carbon_monoxide double precision NOT NULL,
    ozone double precision NOT NULL,
    nitrogen_dioxide double precision NOT NULL,
    sulphur_dioxide double precision NOT NULL,
    pm2_5 double precision NOT NULL,
    pm10 double precision NOT NULL,
    us_epa_index integer NOT NULL,
    gb_defra_index integer NOT NULL
);


--
-- Name: air_quality_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.air_quality_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: air_quality_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.air_quality_id_seq OWNED BY public.air_quality.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: weather_observations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.weather_observations (
    id integer NOT NULL,
    country character varying(100) NOT NULL,
    location_name character varying(100) NOT NULL,
    last_updated timestamp without time zone NOT NULL,
    temperature_celsius double precision NOT NULL,
    condition_text character varying(100) NOT NULL,
    humidity integer NOT NULL,
    wind_kph double precision NOT NULL,
    wind_degree integer NOT NULL,
    wind_direction public.wind_direction NOT NULL,
    sunrise time without time zone NOT NULL,
    sunset time without time zone NOT NULL
);


--
-- Name: weather_observations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.weather_observations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: weather_observations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.weather_observations_id_seq OWNED BY public.weather_observations.id;


--
-- Name: air_quality id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.air_quality ALTER COLUMN id SET DEFAULT nextval('public.air_quality_id_seq'::regclass);


--
-- Name: weather_observations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.weather_observations ALTER COLUMN id SET DEFAULT nextval('public.weather_observations_id_seq'::regclass);


--
-- Name: air_quality air_quality_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.air_quality
    ADD CONSTRAINT air_quality_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: air_quality uq_air_quality_observation; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.air_quality
    ADD CONSTRAINT uq_air_quality_observation UNIQUE (observation_id);


--
-- Name: weather_observations uq_observation; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.weather_observations
    ADD CONSTRAINT uq_observation UNIQUE (country, location_name, last_updated);


--
-- Name: weather_observations weather_observations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.weather_observations
    ADD CONSTRAINT weather_observations_pkey PRIMARY KEY (id);


--
-- Name: ix_weather_observations_country; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_weather_observations_country ON public.weather_observations USING btree (country);


--
-- Name: ix_weather_observations_last_updated; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_weather_observations_last_updated ON public.weather_observations USING btree (last_updated);


--
-- Name: air_quality fk_air_quality_observation; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.air_quality
    ADD CONSTRAINT fk_air_quality_observation FOREIGN KEY (observation_id) REFERENCES public.weather_observations(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict RhF3JcfGH8QXfyBc2JEzCCH0HmO50UER3ycvCiav3YYmU1R7IBRNo5iXBkZh9ny

