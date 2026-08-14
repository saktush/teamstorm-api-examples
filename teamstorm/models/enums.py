from __future__ import annotations

from enum import StrEnum


class AttributeType(StrEnum):
    """
    Swagger: AttributeType -- the kind of value a custom `AttributeModel`
    holds; also the `type` discriminator on `AttributeValueModel` and the
    `Create*FieldRequestBody`/`Update*FieldRequestBody` families in
    `teamstorm/models/workitems_attributes_create.py` and
    `.../workitems_attributes_update.py`.
    """

    UniString = "UniString"
    Number = "Number"
    Date = "Date"
    UniSelect = "UniSelect"
    Tag = "Tag"
    User = "User"
    TimeDuration = "TimeDuration"


class SprintStates(StrEnum):
    """
    Swagger: SprintStates -- lifecycle state of a `SprintModel`.
    """

    New = "New"
    Active = "Active"
    Completed = "Completed"


class TreeNodeType(StrEnum):
    """
    Swagger: TreeNodeType -- the kind of node in a workspace's folder tree,
    e.g. the `type` of a `TreeNodeThumbModel`.
    """

    Folder = "Folder"
    Task = "Task"
    Workspace = "Workspace"
    Document = "Document"


class TypeColor(StrEnum):
    """
    Swagger: TypeColor -- the display color assigned to a `TypeModel`
    (workitem type). Fixed palette of 23 named colors; send exactly one of
    these identifiers.
    """

    Sky = "Sky"
    Mint = "Mint"
    Yellow = "Yellow"
    Amber = "Amber"
    Slate = "Slate"
    Tomato = "Tomato"
    Red = "Red"
    Crimson = "Crimson"
    Pink = "Pink"
    Plum = "Plum"
    Purple = "Purple"
    Violet = "Violet"
    Indigo = "Indigo"
    Blue = "Blue"
    Cyan = "Cyan"
    Teal = "Teal"
    Green = "Green"
    Grass = "Grass"
    Orange = "Orange"
    Brown = "Brown"
    Gold = "Gold"
    Bronze = "Bronze"
    Gray = "Gray"


class TypeIcon(StrEnum):
    """
    Swagger: TypeIcon -- the display icon assigned to a `TypeModel`
    (workitem type). 63 named icon identifiers; treat as an open-ish string
    enum and send exactly one of these identifiers.
    """

    BugSolid = "BugSolid"
    BookmarkSolid = "BookmarkSolid"
    LightningSolid = "LightningSolid"
    LayersSolid = "LayersSolid"
    CrownSolid = "CrownSolid"
    DocSolid = "DocSolid"
    FireSolid = "FireSolid"
    EyeSolid = "EyeSolid"
    LampSolid = "LampSolid"
    StarSolid = "StarSolid"
    CheckmarkCircleSolid = "CheckmarkCircleSolid"
    FlagSolid = "FlagSolid"
    ChartPieSolid = "ChartPieSolid"
    UmbrellaSolid = "UmbrellaSolid"
    WaveformEcgSolid = "WaveformEcgSolid"
    KeySolid = "KeySolid"
    FavoritesSolid = "FavoritesSolid"
    CheckboxSolid = "CheckboxSolid"
    AlertTriangleSolid = "AlertTriangleSolid"
    TraySolid = "TraySolid"
    BoxSolid = "BoxSolid"
    BracketsSolid = "BracketsSolid"
    MessageBubbleSolid = "MessageBubbleSolid"
    SettingsSolid = "SettingsSolid"
    GiftboxSolid = "GiftboxSolid"
    PenSolid = "PenSolid"
    ShieldSolid = "ShieldSolid"
    LockSolid = "LockSolid"
    Square4GridSolid = "Square4GridSolid"
    BookOpenSolid = "BookOpenSolid"
    QuestionCircleSolid = "QuestionCircleSolid"
    MinusCircleSolid = "MinusCircleSolid"
    PlusCircleSolid = "PlusCircleSolid"
    InfoCircleSolid = "InfoCircleSolid"
    ArrowCircleUpSolid = "ArrowCircleUpSolid"
    ArrowCircleDownSolid = "ArrowCircleDownSolid"
    AlertCircleSolid = "AlertCircleSolid"
    CompassSolid = "CompassSolid"
    EmojiFrownSolid = "EmojiFrownSolid"
    EmojiSmileSolid = "EmojiSmileSolid"
    ArrowTurnRightSolid = "ArrowTurnRightSolid"
    ArrowTurnLeftSolid = "ArrowTurnLeftSolid"
    ArrowDownSolid = "ArrowDownSolid"
    ArrowUpSolid = "ArrowUpSolid"
    CheckmarkSolid = "CheckmarkSolid"
    HouseSolid = "HouseSolid"
    ClockSolid = "ClockSolid"
    ArchiveboxSolid = "ArchiveboxSolid"
    HeadphonesSolid = "HeadphonesSolid"
    TgSolid = "TgSolid"
    ShapeRhombusSolid = "ShapeRhombusSolid"
    Poop = "Poop"
    ShapeTriangleSolid = "ShapeTriangleSolid"
    ShapeCircleSolid = "ShapeCircleSolid"
    ShapeSquareSolid = "ShapeSquareSolid"
    TrashSolid = "TrashSolid"
    BrushSolid = "BrushSolid"
    AsteriskSolid = "AsteriskSolid"
    RocketSolid = "RocketSolid"
    LeafSolid = "LeafSolid"
    TriangleCircleSolid = "TriangleCircleSolid"
    Sparkle = "Sparkle"


class ProgressType(StrEnum):
    """
    Swagger: ProgressType -- how a workitem `TypeModel` computes its percent-
    complete: from its status category, from its children's completion, or
    from a numeric metric.
    """

    ByStatus = "ByStatus"
    ByChildren = "ByChildren"
    ByMetric = "ByMetric"


class WorkflowType(StrEnum):
    """
    Swagger: WorkflowType -- whether a `WorkflowModel` governs workitem
    statuses/transitions or portfolio-element statuses/transitions.
    """

    Workitem = "Workitem"
    Portfolio = "Portfolio"


class EstimatesType(StrEnum):
    """
    Swagger: EstimatesType -- the estimation scheme an `AgileModel` board
    uses (time-based or story-point-based).

    NOTE: same name, but NOT the same object, as the `EstimatesType = str`
    alias local to `teamstorm/models/agile.py` -- `teamstorm/api/agile.py`
    imports the `agile.py` alias, not this enum. See
    `docs/api-analysis/conventions.md` §10 gotcha 4.
    """

    EstimatesInTime = "EstimatesInTime"
    EstimatesInStoryPoints = "EstimatesInStoryPoints"


class ProviderType(StrEnum):
    """
    Swagger: ProviderType -- the authentication provider a `UserModel`/
    `GroupModel` was provisioned from.
    """

    Local = "Local"
    ActiveDirectory = "ActiveDirectory"
    OpenIdConnect = "OpenIdConnect"
    KerberosActiveDirectory = "KerberosActiveDirectory"


class PrincipalType(StrEnum):
    """
    Swagger: PrincipalType -- discriminator for a comment/query access-list
    principal: is this entry a user or a group.

    NOTE: same two members as `SharedItemAccessType` below, but per
    `docs/api-analysis/upstream-semantics.md` ("SharedItemAccessType /
    PrincipalType") these are two separate upstream C# enum types used in
    different contexts (comment/query access-list principal vs. sharing-
    permission subject) -- kept as distinct StrEnums rather than merged, to
    avoid conflating two independently-versioned concepts that only
    coincidentally share member names today.
    """

    User = "User"
    Group = "Group"


class CommentVisibilityType(StrEnum):
    """
    Swagger: CommentVisibilityType -- who besides the comment's author can
    see a comment: everyone, the workspace, or an explicit access list
    (included via `OnlySelected` or excluded via `ExceptSelected`).
    """

    All = "All"
    Workspace = "Workspace"
    OnlySelected = "OnlySelected"
    ExceptSelected = "ExceptSelected"


class SharedItemAccessType(StrEnum):
    """
    Swagger: SharedItemAccessType -- discriminator ("type") for a workitem/
    document sharing permission's subject: is this a per-user grant or a
    per-group grant.

    NOTE: same two members as PrincipalType above, but per
    docs/api-analysis/upstream-semantics.md ("SharedItemAccessType /
    PrincipalType") these are two separate upstream C# enum types used in
    different contexts (sharing-permission subject vs. comment access-list
    principal) -- kept as distinct StrEnums here rather than reusing
    PrincipalType, to avoid conflating two independently-versioned concepts
    that only coincidentally share member names today.
    """

    User = "User"
    Group = "Group"


class SharedItemAccessLevel(StrEnum):
    """
    Swagger: SharedItemAccessLevel -- the access level granted by a
    workitem/document sharing permission. Confirmed against
    docs/api-analysis/upstream-semantics.md ("SharedItemAccessLevel").
    """

    Read = "Read"
    Edit = "Edit"
    Comment = "Comment"


class QueryVisibilityType(StrEnum):
    """
    Swagger: QueryVisibilityType -- who besides the query's author can see a
    saved query and its results.

    NOTE: same 4 shapes as CommentVisibilityType but a genuinely distinct
    upstream C# enum with different member names ("Author" here vs. "All"
    there) -- kept separate rather than reused, per
    docs/api-analysis/upstream-semantics.md "QueryVisibilityType".

    Validation rule enforced server-side (not by this API wrapper): if Author/
    Workspace, accessList must be empty; if OnlySelected/ExceptSelected,
    accessList must have >=1 entry; the query's own author cannot appear in
    the access list.
    """

    Author = "Author"
    Workspace = "Workspace"
    OnlySelected = "OnlySelected"
    ExceptSelected = "ExceptSelected"


class AntivirusScanVerdict(StrEnum):
    """
    Swagger: AntivirusScanVerdict -- outcome of the out-of-band antivirus
    scan run on an uploaded attachment. A file whose verdict is not yet
    "NotDetected" (i.e. "WaitToScan"/"Processing", or a "Detected" hit)
    surfaces as 423 Locked when downloaded -- see
    docs/api-analysis/upstream-semantics.md "Attachment upload/download
    flow".
    """

    WaitToScan = "WaitToScan"
    Detected = "Detected"
    NotDetected = "NotDetected"
    Processing = "Processing"
    Error = "Error"
    Skipped = "Skipped"


class TokenType(StrEnum):
    """
    Swagger: TokenType -- the external git host a GitIntegrationTokens
    credential authenticates against.
    """

    GitLab = "GitLab"
    GitFlic = "GitFlic"


class SystemRoles(StrEnum):
    """
    Swagger: SystemRoles -- fixed system-level roles usable only in OpenID
    pre-provisioning (CreateOpenIdUserModel.roles). Confirmed against
    docs/api-analysis/upstream-semantics.md ("SystemRoles ... used only in
    OpenID pre-provisioning").
    """

    CoreAdmin = "CoreAdmin"
    CwmAdmin = "CwmAdmin"
    CwmUser = "CwmUser"
    SecurityOfficer = "SecurityOfficer"
    CwmGuest = "CwmGuest"
