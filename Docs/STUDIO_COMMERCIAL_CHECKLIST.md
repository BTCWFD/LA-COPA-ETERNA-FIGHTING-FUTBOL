# Checklist de Finalización Comercial AAA — **LA COPA ETERNA: SANGRE Y POTRERO**

Este documento recoge los últimos pasos de estudio necesarios para pasar del prototipo jugable/standalone empaquetado (`UE 5.8.4` + `WebLab`) a lanzamiento comercial en tiendas (**Steam, Epic Games Store, PS5, Xbox Series X|S**).

---

## 1. Epic Online Services (EOS) & Crossplay GGPO
- [ ] Registrar el producto en [Epic Games Developer Portal](https://dev.epicgames.com/).
- [ ] Rellenar `ProductId`, `SandboxId`, `DeploymentId`, `ClientId`, `ClientSecret` y `EncryptionKey` en `Config/DefaultEOS.ini` y `Backend/.env` (ver `Backend/.env.example`).
- [ ] Habilitar `WITH_EOS_SDK=1` en `Source/SouthAmericaFightersCore/SouthAmericaFightersCore.Build.cs` con el SDK oficial de EOS incluido en `UE 5.8` para compilar los sockets P2P NAT Traversal reales.
- [ ] Activar pruebas de latencia cruzada entre nodos de Sudamérica (São Paulo, Buenos Aires, Santiago, Bogotá, Lima).

## 2. Producción de Audio Final en Audiokinetic Wwise 2023.1+
- [ ] Instalar **Wwise Launcher** e integrar el plugin `Wwise` en `SouthAmericaFighters.uproject`.
- [ ] Grabar voces reales en estudio para los **35 eventos `Play_VO_*` / `Play_Intro_*`** definidos en `Data/DT_CommentaryAndRivalries.json`.
- [ ] Reemplazar los stems temporales de `Audio/GeneratedStems/` (19 archivos 48 kHz 16-bit) por grabaciones de batucada, bombo murga, candombe, cueca, polka, cajón, sanjuanito y joropo, y compilar los `.bnk` hacia `Content/WwiseAudio/`.

## 3. Arte 3D High-Poly, Escultura & Animaciones Mocap (Blender 5.2 → UE 5.8.4)
- [ ] Abrir `Assets/BlenderProduction/Fighters/Master_17Fighters_Showcase.blend` y `Assets/BlenderProduction/Stages/Master_Maracana_And_Centenario.blend` en **Blender 5.2.1 LTS**.
- [ ] Esculpir anatomía *high-poly* / rostros detallados estilo *Renacimiento Sfumato* y hacer *bake* de mapas Normal/AO sobre los 17 personajes preservando los 38 huesos y `ChaosCloth_Jersey_Weight`.
- [ ] Re-ejecutar `Scripts/blender_fighters_ue5_pipeline.py` y `Scripts/ue5_auto_import_pipeline.py` (o importar directamente desde `Assets/BlenderProduction/Fighters/*.fbx`).
- [ ] Pintar/ajustar en **Unreal Editor** el vértice físico *Chaos Cloth* sobre los `USkeletalMesh` para simulación 60 Hz de camisetas y melenas.

## 4. Arte 2D *Renacimiento Sfumato* (7 Escenarios Pendientes)
- [x] Completados (9 lienzos *Sfumato*): Trofeo Copa Eterna, Key Art, VS Screen, Boss `V.A.R.-ZERO`, Roster Wave 1, Roster Wave 2, Bolivia 3600m, Centenario Uruguay, Volcán de Quito.
- [ ] Generar los 7 escenarios restantes (cuando haya cuota en Gemini Web o Midjourney/Flux): *Templo do Maracanã*, *La Caldera de La Boca*, *Coloso de Barranquilla*, *Coliseo de Ñuñoa*, *El Fortín de Sajonia*, *Templo José Díaz* y *Monumental del Ávila*.

## 5. Despliegue Cloud eSports & Certificación
- [ ] Configurar PostgreSQL + Redis + HTTPS/TLS en la nube ejecutando `Backend/deploy-prod.ps1 -Mode Docker`.
- [ ] Ejecutar empaquetado final en modo `Shipping` para tiendas con `RunUAT.bat BuildCookRun -clientconfig=Shipping`.
- [ ] Pasar certificación TCR/XR para PS5, Xbox Series X|S, Steam Deck y clasificación ESRB/PEGI.
