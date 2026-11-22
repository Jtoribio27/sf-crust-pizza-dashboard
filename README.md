# San Francisco Crust Pizza – Sistema Inteligente de Apoyo a la Toma de Decisiones

Dashboard comercial en Streamlit con asistente de IA (Google Gemini).
Actividad 1 · Sistemas de Información para la Toma de Decisiones · Máster en Dirección Comercial y Ventas (UNIR).

## Contenido

```
app.py                          Aplicación completa
requirements.txt                Librerías necesarias
data/Ventas.xlsx                Base de ventas (se puede sustituir desde la app)
data/Clientes.xlsx              Base de clientes
data/Productos.xlsx             Base de productos
.streamlit/secrets.toml.ejemplo Modelo de configuración de la clave de IA
.gitignore                      Evita subir la clave real a GitHub
```

## Publicación paso a paso (unos 20 minutos)

### 1. Clave de IA (Google AI Studio)
1. Entra en https://aistudio.google.com con una cuenta de Google.
2. Pulsa **Get API key → Create API key** y copia la clave.
3. En AI Studio revisa qué modelo "Flash" está disponible y copia su nombre exacto (por ejemplo `gemini-flash-latest`). Los nombres cambian con el tiempo.

### 2. Repositorio en GitHub
1. Crea una cuenta en https://github.com si no la tienes.
2. **New repository** → nombre `sf-crust-pizza-dashboard` → **Public** → Create.
3. **Add file → Upload files** y arrastra TODO el contenido de esta carpeta (incluida la carpeta `data`).
   Si la carpeta `.streamlit` no se sube por estar oculta, no pasa nada: la clave se configura en el paso 3.
4. Pulsa **Commit changes**.

### 3. Publicar en Streamlit Community Cloud
1. Entra en https://share.streamlit.io e inicia sesión con GitHub.
2. **Create app → Deploy a public app from GitHub**.
3. Repositorio: `sf-crust-pizza-dashboard` · Branch: `main` · Main file: `app.py`.
4. En **Advanced settings → Secrets** pega (con tu clave real):
   ```
   GEMINI_API_KEY = "tu-clave"
   GEMINI_MODEL = "gemini-flash-latest"
   ```
5. Pulsa **Deploy**. En 2-3 minutos tendrás un enlace público `https://....streamlit.app`.
6. Ábrelo en una ventana de incógnito para confirmar que no pide iniciar sesión.

### 4. Antes de la evaluación
- Las apps gratuitas se "duermen" tras horas sin visitas. Ábrela el día antes de entregar y durante la semana de evaluación.
- Si el asistente da error de modelo, cambia `GEMINI_MODEL` en Settings → Secrets por el nombre vigente en AI Studio. No hace falta tocar el código.

## Actualización de datos (requisito 4)
En la barra lateral, **📂 Actualizar bases de datos** → subir un nuevo archivo de Ventas (.xlsx o .csv) con las mismas columnas.
Todos los KPIs, gráficas y el contexto del asistente se recalculan sin modificar el código.
Para el vídeo puede usarse `Ventas_prueba_solo_2025.xlsx`: al subirlo, las ventas pasan de $1,357,882 a $574,105.

## Cifras de control (sin filtros, base original)
| KPI | Valor |
|---|---|
| Ventas totales | $1,357,882 |
| Utilidad bruta | $813,714 |
| Margen bruto | 59.9 % |
| Ticket promedio | $29.58 |
| Clientes | 1,000 |
| Transacciones | 45,900 |
