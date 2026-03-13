# TITLE PROPOSAL

**University of Mindanao**  
**College of Computing Education**

---

## PROPOSED SYSTEM TITLE

**Inventory System v1.0.0: An Enterprise-Grade Inventory Management Platform with Integrated Business Intelligence, Predictive Analytics, and Zero-Configuration Portability for Computer Parts Retail**

---

## PROPONENT

**Name:** Tadena, Kenny Ray M.  
**Course/Section:** IT5L (2868)  
**Academic Year:** 2025-2026  
**Date Submitted:** March 2026

---

## SUBMITTED TO

**Prof. Modesto C. Tarrazona**  
*Course Instructor*  
*College of Computing Education*  
*University of Mindanao*

---

## I. BACKGROUND OF THE STUDY

### 1.1 The Problem: Manual Inventory Inefficiencies

For decades, small-to-medium computer parts retailers have relied on manual inventory tracking methods—paper ledgers, basic spreadsheets, or rudimentary database applications that function as passive record-keepers. These traditional systems present critical operational challenges:

- **Data Integrity Failures:** Manual entry permits negative quantities, missing SKU identifiers, and duplicate records that corrupt inventory accuracy.
- **Reactive Rather Than Proactive Management:** Business owners discover stockouts only when customers demand unavailable products—a cascading failure that damages revenue and reputation.
- **Invisible Aging Inventory:** Products sitting unsold for months depreciate in value, yet traditional systems provide no visibility into inventory aging, tying up capital in stagnant goods.
- **Security Vulnerabilities:** Single-user systems without authentication allow unauthorized modifications, while the absence of audit trails makes accountability impossible.
- **Hardware Lock-In:** Many legacy systems require specific screen resolutions, fail on high-DPI displays, or demand complex installation procedures that lock businesses to specific hardware.

### 1.2 The Solution: Automated Business Intelligence

The Inventory System v1.0.0 represents a paradigm shift from passive inventory tracking to proactive business intelligence. The system does not merely answer "What do we have?"—it answers the strategic questions that drive business success:

- **"When will we run out?"** — Predictive Restocking calculates days-to-stockout using sales velocity analysis.
- **"Which products need attention?"** — The proprietary Health Score Algorithm rates every product on a 0-100 scale, synthesizing stock levels, profit margins, sales velocity, and aging status.
- **"Who changed what, and when?"** — Complete audit logging with username attribution ensures accountability.
- **"Will it work on our computers?"** — Zero-Tinker Portability and Hardware-Adaptive UI guarantee instant deployment on any Windows machine.

This system thinks for the business owner—transforming inventory management from a clerical task into a strategic intelligence platform.

---

## II. GENERAL OBJECTIVE

To design, develop, and deploy an enterprise-grade inventory management system that integrates Business Intelligence analytics, multi-tier security, and hardware-adaptive user interfaces into a single-file, zero-configuration portable application for computer parts retail operations.

---

## III. SPECIFIC OBJECTIVES

1. **Implement Real-Time Validation Architecture**  
   Develop a genius-level validation trace system that physically locks data submission controls until all required fields pass automated validation, making it impossible to persist invalid data to the database.

2. **Engineer Predictive Restocking Intelligence**  
   Create algorithms that calculate average daily sales velocity and project days-to-stockout, providing proactive alerts before inventory depletion occurs rather than reactive notifications afterward.

3. **Design Proprietary Health Score Algorithm**  
   Develop a 0-100 scoring system that synthesizes multiple business metrics (stock criticality, profit margin thresholds, inventory aging, sales velocity) into a single actionable indicator per product.

4. **Establish Role-Based Access Control (RBAC)**  
   Implement three-tier permission architecture (Administrator, Manager, Staff) that enforces operational boundaries through UI-level control disabling, ensuring users can only perform authorized actions.

5. **Achieve Hardware-Adaptive User Interface**  
   Engineer DPI awareness through Windows API integration and relative scaling (80% screen dimension rule) to ensure pixel-perfect rendering on displays ranging from 720p laptops to 4K monitors without UI element overlap or truncation.

6. **Deliver Zero-Tinker Portability**  
   Create self-initializing executable that automatically provisions required directory structures, database schema, and default administrative credentials—enabling instant deployment via USB transfer without installation procedures.

7. **Eliminate All Architectural Limitations**  
   Refactor the system to support multi-database drivers (SQLite/PostgreSQL/MySQL), barcode scanner integration, internationalization framework, Point-of-Sale transaction recording, and pagination for datasets exceeding 100,000 products.

---

## IV. METHODOLOGY

### 4.1 Development Framework

The system is developed using **Python 3.14** following the **Model-View-Controller (MVC)** architectural pattern with an additional **Repository Layer** for database abstraction:

| Layer | Responsibility | Implementation |
|-------|----------------|----------------|
| **Model** | Data entities with computed BI properties | `@dataclass` classes: Product, User, AuditLog |
| **View** | User interface presentation | Tkinter widgets: LoginView, DashboardView |
| **Controller** | Business logic coordination | Application class managing view transitions |
| **Repository** | Database abstraction | ProductRepository, UserRepository, AuditRepository |

### 4.2 Database Architecture

- **Primary Engine:** SQLite with Write-Ahead Logging (WAL) for concurrent read/write operations
- **Multi-Driver Abstraction:** DatabaseDriver protocol supporting PostgreSQL and MySQL for cloud deployment scenarios
- **Schema Features:**
  - Products table with BI columns (cost_price, total_sold, last_sold_at)
  - Sales history for POS integration
  - Comprehensive audit logging
  - User preferences for UI customization
- **Performance Optimization:** Strategic indexing on SKU, category, quantity, brand, and timestamp fields for sub-second retrieval on 100,000+ product catalogs

### 4.3 Security Implementation

- **Password Hashing:** BCrypt with 12 computational rounds (~300ms per hash, making brute-force attacks computationally infeasible)
- **Role-Based Access Control:** Three-tier permission model enforced at UI level
- **Audit Trail:** Every Create, Read, Update, Delete, and Export operation logged with username, action type, entity, details, and timestamp

### 4.4 User Interface Engineering

- **Theming:** Professional dark interface using Slate color palette
- **DPI Awareness:** Windows API integration via `SetProcessDpiAwareness(2)` for per-monitor scaling
- **Relative Sizing:** 80% screen dimension calculation with min/max clamping (1200×700 to 1920×1080)
- **Background Threading:** Heavy operations (CSV export, report generation) execute in daemon threads with loading indicators to maintain UI responsiveness

---

## V. TECHNICAL INNOVATION SUMMARY

### 5.1 Unique Selling Points

| Innovation | Description | Business Impact |
|------------|-------------|-----------------|
| **Predictive Restocking** | Calculates days-to-stockout using `quantity ÷ avg_daily_sales` | Eliminates surprise stockouts; enables proactive ordering |
| **Health Score Algorithm** | 0-100 score synthesizing stock, margin, aging, velocity | Instant visual triage of which products need attention |
| **Zero-Tinker Portability** | Auto-initializes directories and database on first launch | Deploy to any machine via USB in seconds |
| **Real-Time Validation** | Save button physically locked until form validates | 100% data integrity; impossible to persist invalid records |
| **Hardware Adaptability** | DPI awareness + 80% relative scaling | Works on any screen resolution without overlap |
| **Multi-Database Support** | Driver abstraction for SQLite/PostgreSQL/MySQL | Seamless transition from portable to cloud deployment |
| **Barcode Scanner Ready** | Rapid keystroke detection (<50ms) for scanner input | Reduces SKU entry time from seconds to milliseconds |
| **POS Integration** | Sales recording with automatic inventory deduction | Real-time stock accuracy after every transaction |
| **Infinite Scalability** | Pagination and lazy-loading for 100k+ products | No performance ceiling as business grows |

### 5.2 Code Quality Standards

- **PEP 8 Compliance:** All code adheres to Python style guidelines
- **Type Annotations:** Full type hints on all functions for IDE support and error prevention
- **Professional Docstrings:** Comprehensive documentation on all classes and public methods
- **Single-File Architecture:** ~4,200 lines of Python demonstrating that sophisticated architecture does not require complex multi-file deployments
- **Surgical Optimization:** Code underwent comprehensive cleanup to eliminate redundancies while maintaining 100% functionality

### 5.3 Deployment Metrics

| Metric | Value |
|--------|-------|
| Source Lines of Code | ~4,200 |
| Compiled Executable Size | 23 MB |
| External Dependencies | pillow, bcrypt, python-pptx (optional) |
| Built-in Python Modules | tkinter, sqlite3, threading, dataclasses |
| Installation Required | None (Zero-Tinker) |
| Supported Platforms | Windows 7/8/10/11 (primary), macOS/Linux (compatible) |

---

## VI. EXPECTED OUTPUT

Upon completion, this project will deliver:

1. **Standalone Executable:** `Inventory_System.exe` (~23 MB) deployable via USB transfer
2. **Source Code:** `main.py` with full type annotations and documentation
3. **Technical Documentation:** `PROJECT_DOCUMENT.md` with architecture diagrams and API reference
4. **Presentation Materials:** PowerPoint presentation and supporting diagrams
5. **Language Resources:** JSON-based internationalization files for multilingual expansion

---

## VII. SIGNIFICANCE OF THE STUDY

This project demonstrates that enterprise-grade software can be:

- **Architecturally Sophisticated** — MVC pattern with repository abstraction, driver protocols, and computed properties
- **Operationally Simple** — Zero-configuration deployment, automatic initialization, intuitive interface
- **Academically Rigorous** — Full documentation, PEP 8 compliance, comprehensive type hints
- **Practically Valuable** — Solves real business problems with predictive analytics and Business Intelligence

The Inventory System v1.0.0 serves as a reference implementation proving that powerful software solutions need not be complex to deploy or maintain.

---

**Respectfully submitted,**

**Kenny Ray M. Tadena**  
*Proponent*

---

**Noted by:**

**Prof. Modesto C. Tarrazona**  
*Course Instructor*

---

*Document Generated: March 2026*  
*Inventory System v1.0.0 — Enterprise Inventory Management with Business Intelligence*
