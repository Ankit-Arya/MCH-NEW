from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
BACKEND = PROJECT / "backend"
FRONTEND = PROJECT / "frontend"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    print(f"updated {path.relative_to(PROJECT)}")


def patch_models() -> None:
    path = BACKEND / "app" / "models" / "all_models.py"
    text = read(path)
    if "class HelpTopic" in text:
        print("models already contain Help Forum tables")
        return

    block = '''\n\nclass HelpTopic(Base, TimestampMixin):\n    __tablename__ = "help_topics"\n    id: Mapped[int] = mapped_column(primary_key=True)\n    title: Mapped[str] = mapped_column(String(240), nullable=False, index=True)\n    body: Mapped[str] = mapped_column(Text, nullable=False)\n    status: Mapped[str] = mapped_column(String(40), default="OPEN", nullable=False, index=True)\n    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)\n    answered_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))\n    answered_at: Mapped[datetime | None] = mapped_column(DateTime)\n    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)\n    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)\n    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)\n\n    author: Mapped[User] = relationship(foreign_keys=[created_by])\n    answerer: Mapped[User | None] = relationship(foreign_keys=[answered_by])\n    comments: Mapped[list["HelpComment"]] = relationship(back_populates="topic", cascade="all, delete-orphan")\n    media: Mapped[list["HelpMedia"]] = relationship(back_populates="topic", cascade="all, delete-orphan")\n\n\nclass HelpComment(Base, TimestampMixin):\n    __tablename__ = "help_comments"\n    id: Mapped[int] = mapped_column(primary_key=True)\n    topic_id: Mapped[int] = mapped_column(ForeignKey("help_topics.id"), nullable=False, index=True)\n    body: Mapped[str] = mapped_column(Text, nullable=False)\n    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)\n    is_admin_answer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)\n    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)\n\n    topic: Mapped[HelpTopic] = relationship(back_populates="comments")\n    author: Mapped[User] = relationship()\n    media: Mapped[list["HelpMedia"]] = relationship(back_populates="comment")\n\n\nclass HelpMedia(Base, TimestampMixin):\n    __tablename__ = "help_media"\n    id: Mapped[int] = mapped_column(primary_key=True)\n    topic_id: Mapped[int] = mapped_column(ForeignKey("help_topics.id"), nullable=False, index=True)\n    comment_id: Mapped[int | None] = mapped_column(ForeignKey("help_comments.id"), index=True)\n    object_path: Mapped[str] = mapped_column(String(500), nullable=False)\n    original_file_name: Mapped[str] = mapped_column(String(250), nullable=False)\n    mime_type: Mapped[str | None] = mapped_column(String(120))\n    file_size: Mapped[int | None] = mapped_column(Integer)\n    checksum: Mapped[str | None] = mapped_column(String(128), index=True)\n    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)\n    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)\n    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)\n\n    topic: Mapped[HelpTopic] = relationship(back_populates="media")\n    comment: Mapped[HelpComment | None] = relationship(back_populates="media")\n    uploader: Mapped[User] = relationship()\n'''

    marker = "\n\nclass AuditLog(Base):"
    if marker not in text:
        raise RuntimeError("Could not find AuditLog marker in all_models.py")
    text = text.replace(marker, block + marker)
    write(path, text)


def patch_backend_router() -> None:
    path = BACKEND / "app" / "api" / "v1" / "router.py"
    text = read(path)
    if "help.router" in text:
        print("backend router already includes Help Forum")
        return

    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if line.startswith("from app.api.v1.endpoints import ") and "help" not in line:
            lines[idx] = line + ", help"
            break
    text = "\n".join(lines) + "\n"
    insert = 'api_router.include_router(help.router, prefix="/help", tags=["Help Forum"])\n'
    marker = 'api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])\n'
    if marker in text:
        text = text.replace(marker, insert + marker)
    else:
        text += insert
    write(path, text)


def patch_frontend_router() -> None:
    path = FRONTEND / "src" / "router" / "index.js"
    text = read(path)
    changed = False
    if "HelpForumView" not in text:
        text = text.replace("import WeeklyComplianceView from '../views/WeeklyComplianceView.vue'", "import WeeklyComplianceView from '../views/WeeklyComplianceView.vue'\nimport HelpForumView from '../views/HelpForumView.vue'")
        changed = True
    if "path: '/help'" not in text:
        marker = "  { path: '/reports', component: ReportsView, meta: { requiresAuth: true } },"
        route = "  { path: '/help', component: HelpForumView, meta: { requiresAuth: true } },\n"
        if marker not in text:
            raise RuntimeError("Could not find reports route in frontend router")
        text = text.replace(marker, route + marker)
        changed = True
    if changed:
        write(path, text)
    else:
        print("frontend router already includes Help Forum")


def patch_app_layout() -> None:
    path = FRONTEND / "src" / "components" / "AppLayout.vue"
    text = read(path)
    if 'to="/help"' in text:
        print("AppLayout already contains Help Forum link")
        return

    marker = '        <RouterLink to="/reports" @click="closeMobileMenu">Reports & PDFs</RouterLink>'
    insert = '        <RouterLink to="/help" @click="closeMobileMenu">Help Forum</RouterLink>\n'
    if marker not in text:
        raise RuntimeError("Could not find Reports & PDFs navigation link in AppLayout.vue")
    text = text.replace(marker, insert + marker)
    write(path, text)


if __name__ == "__main__":
    patch_models()
    patch_backend_router()
    patch_frontend_router()
    patch_app_layout()
    print("Help Forum patch applied. Now run the SQL migration and rebuild api/frontend.")
