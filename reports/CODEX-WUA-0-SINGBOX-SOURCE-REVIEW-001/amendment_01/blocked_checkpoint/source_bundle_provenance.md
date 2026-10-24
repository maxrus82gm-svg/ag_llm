# Что отсутствует

Нужен **один официальный source archive sing-box v1.13.4** для revision **d09182614c7778c1e0f51d990635c5d4249c437e**. Локальный путь/архив/package hash/transfer receipt не получены. Точечная проверка proposed destination дала file absent; широкого поиска не было. `evidence/bundle_request.json` фиксирует этот предел проверки.

Переданные координатором upstream references: [release v1.13.4](https://github.com/SagerNet/sing-box/releases/tag/v1.13.4), [точная revision](https://github.com/SagerNet/sing-box/tree/d09182614c7778c1e0f51d990635c5d4249c437e). Это ссылки из утверждённой постановки; локальный Codex их не открывал и архив не скачивал. Подтверждение tag→commit принадлежит WEB_11, не текущему локальному source review.

Для chain of custody нужны имя/размер/SHA256 **архива**, официальный origin/revision и сведения о передаче. Hash установленного EXE не использовать вместо package hash. После получения следует проверить фактические архивные bytes, состав и matching go.mod/go.sum/source tree. Versioned docs/schema учитывать только если они реально доступны в поставке; не создавать якобы upstream schema из собственного шаблона.

Source→binary reproducible correspondence/подпись EXE остаются отдельными вопросами. Даже подлинные исходники и совпадающий embedded commit не доказывают подлинность конкретного установленного бинарника или эффективную Windows policy.
