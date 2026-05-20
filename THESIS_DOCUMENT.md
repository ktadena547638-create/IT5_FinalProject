# INVENTORY SYSTEM v1.1.0
## Enterprise Inventory Management with Embedded Business Intelligence
### A Comprehensive Thesis on Portable, Intelligent Inventory Optimization

Author: Kenny Ray M. Tadena
Course: IT5L (2868)
Instructor: Prof. Modesto C. Tarrazona
Date: May 2026
Version: 1.1.0

---

## EXECUTIVE SUMMARY

The Inventory System v1.1.0 documents important improvements for small-to-medium computer parts retailers. Building on the original portable design, this revision emphasizes stability, usability, and modularization. It addresses component obsolescence, volatile pricing, supplier complexity, and the need for just-in-time inventory management without server infrastructure.

This work describes the design, implementation, hardening, and validation of an intelligent, single-machine inventory management platform. Improvements since v1.0.0 include modular extraction of shared core types, hardened background-task scheduling, fixes to dashboard actions such as Export CSV and Generate Report, expanded reporting that includes receipts and current inventory, improved POS lookup by SKU or product name, category normalization, persistence fixes for deletions, a first-run admin setup replacing seeded credentials, and packaging/build hardening. These changes preserve the original architecture while improving reliability and maintainability.

---

## 1. INTRODUCTION

### 1.1 The Evolution of Inventory Management

Inventory management remains at the operational heart of retail commerce. From ledger systems to cloud platforms, the enduring challenge is matching supply to demand while minimizing stockouts and excess inventory. Small retailers, especially computer parts shops with limited IT infrastructure and staffing, face a persistent gap between operational needs and available solutions.

Enterprise resource planning and point-of-sale systems often demand complex server deployments, database administration, and ongoing maintenance. For a small shop with one or two employees, these solutions impose financial and operational friction. Inventory tracking becomes manual and error-prone, optimization decisions rely on intuition rather than data, and untracked inventory leads to silent financial losses.

### 1.2 Project Vision and Problem Statement

The Inventory System v1.0.0 was created to close the gap for small retailers. It was designed around three principles: portability, intelligence, and accessibility.

Portability: the application, including database, user interface, analytics, and security, is packaged as a single executable. No server setup or network configuration is required; a retailer can launch the executable from a USB drive and begin managing inventory immediately.

Intelligence: the system analyzes inventory patterns, computes per-product health metrics (profit margin, days-to-stockout, aging scores), and issues proactive alerts. It functions as an analytical advisor rather than a passive ledger.

Accessibility: beyond a simple UI, the application provides role-based access control, audit logging for compliance, and hardware-adaptive design that works across older laptops and modern high-DPI displays.

### 1.3 Technical Foundation and Architectural Philosophy

The system follows clean separation of concerns to enable future scaling without redesign. The codebase has been modularized: shared dataclasses and configuration are in `core.py`, background execution helpers in `utils/background_task.py`, and audit and preferences helpers in `utils/repositories_aux.py`. The repository pattern abstracts data access and supports migration between SQLite and server-backed databases such as PostgreSQL or MySQL.

The database uses SQLite with Write-Ahead Logging (WAL) for ACID compliance and concurrent reads. Security uses bcrypt for password hashing with a cost factor of 12, and audit logging captures user actions for compliance and forensics.

The UI is implemented with Tkinter and provides a native look across Windows, macOS, and Linux. It adapts to monitor DPI to ensure legibility and proper layout on both standard and high-resolution displays.

### 1.4 Technological Stack and Design Decisions

Core Language: Python 3.14 was chosen for rapid development, its ecosystem, and packaging with PyInstaller.

Database: SQLite with WAL mode is used for local deployments; PostgreSQL and MySQL drivers are available for multi-user deployments.

User Interface: Tkinter with ttk widgets provides a native look without external dependencies.

Security: bcrypt with cost factor 12 secures passwords; the system uses role-based access control.

Imaging: Pillow supports product photography and thumbnail generation.

Analytics: custom algorithms implement inventory health scoring, demand forecasting, and aging detection.

Deployment: PyInstaller packages the application into a single executable; `build.ps1` automates packaging. Recent builds produced a reproducible single-file executable (dist\CIS.exe) around 23.4–23.6 MB after optimization.

---

## 2. PROBLEM ANALYSIS AND JUSTIFICATION

### 2.1 Market Gap and Business Context

Computer parts retailers face several challenges that generic inventory systems do not address. Component obsolescence is rapid: inventory can lose market value within months. Pricing volatility in semiconductor markets can compress margins quickly. Suppliers vary in lead time and minimum order quantities, complicating restocking decisions. Small retailers also lack dedicated inventory analysts, so the system must provide quick insights via dashboards and alerts rather than deep analytic queries.

### 2.2 Specific Problems Addressed

The Inventory System addresses key operational pain points. It improves inventory accuracy through schema and transaction controls, reducing manual errors. Restocking intelligence predicts days-to-stockout using sales velocity so critical items are surfaced before depletion. Profit optimization is enabled by per-product margin calculations and recommendations for low-margin items. Aging inventory is detected by tracking days-in-inventory and flagging items beyond thresholds for clearance. The system implements role-based permissions and comprehensive audit logging for security and compliance. Finally, operational friction is reduced by single-file deployment, automatic database initialization, and an intuitive user experience requiring minimal training.

---

## 3. PROJECT OBJECTIVES

### 3.1 Primary Objectives

The project pursued four objectives. First, deliver an end-to-end inventory solution for product master data, stock tracking, sales recording, and reporting without external services. Second, embed business intelligence to compute metrics, flag anomalies, and provide data-driven recommendations. Third, ensure enterprise-grade security with encrypted password storage, RBAC, and audit logging. Fourth, maximize accessibility by enabling zero-infrastructure deployment as a single file that runs on minimal hardware.

INVENTORY SYSTEM v1.1.0
Enterprise Inventory Management with Embedded Business Intelligence
A Comprehensive Thesis on Portable, Intelligent Inventory Optimization

Author: Kenny Ray M. Tadena
Course: IT5L (2868)
Instructor: Prof. Modesto C. Tarrazona
Date: May 2026
Version: 1.1.0

---

EXECUTIVE SUMMARY

The Inventory System v1.1.0 documents important improvements for small-to-medium computer parts retailers. Building on the original portable design, this revision emphasizes stability, usability, and modularization. It addresses component obsolescence, volatile pricing, supplier complexity, and the need for just-in-time inventory management without server infrastructure.

This work describes the design, implementation, hardening, and validation of an intelligent, single-machine inventory management platform. Improvements since v1.0.0 include modular extraction of shared core types, hardened background-task scheduling, fixes to dashboard actions such as Export CSV and Generate Report, expanded reporting that includes receipts and current inventory, improved POS lookup by SKU or product name, category normalization, persistence fixes for deletions, a first-run admin setup replacing seeded credentials, and packaging/build hardening. These changes preserve the original architecture while improving reliability and maintainability.

---

1. INTRODUCTION

1.1 The Evolution of Inventory Management

Inventory management remains at the operational heart of retail commerce. From ledger systems to cloud platforms, the enduring challenge is matching supply to demand while minimizing stockouts and excess inventory. Small retailers, especially computer parts shops with limited IT infrastructure and staffing, face a persistent gap between operational needs and available solutions.

Enterprise resource planning and point-of-sale systems often demand complex server deployments, database administration, and ongoing maintenance. For a small shop with one or two employees, these solutions impose financial and operational friction. Inventory tracking becomes manual and error-prone, optimization decisions rely on intuition rather than data, and untracked inventory leads to silent financial losses.

1.2 Project Vision and Problem Statement

The Inventory System v1.0.0 was created to close the gap for small retailers. It was designed around three principles: portability, intelligence, and accessibility.

Portability: the application, including database, user interface, analytics, and security, is packaged as a single executable. No server setup or network configuration is required; a retailer can launch the executable from a USB drive and begin managing inventory immediately.

Intelligence: the system analyzes inventory patterns, computes per-product health metrics (profit margin, days-to-stockout, aging scores), and issues proactive alerts. It functions as an analytical advisor rather than a passive ledger.

Accessibility: beyond a simple UI, the application provides role-based access control, audit logging for compliance, and hardware-adaptive design that works across older laptops and modern high-DPI displays.

1.3 Technical Foundation and Architectural Philosophy

The system follows clean separation of concerns to enable future scaling without redesign. The codebase has been modularized: shared dataclasses and configuration are in `core.py`, background execution helpers in `utils/background_task.py`, and audit and preferences helpers in `utils/repositories_aux.py`. The repository pattern abstracts data access and supports migration between SQLite and server-backed databases such as PostgreSQL or MySQL.

The database uses SQLite with Write-Ahead Logging (WAL) for ACID compliance and concurrent reads. Security uses bcrypt for password hashing with a cost factor of 12, and audit logging captures user actions for compliance and forensics.

The UI is implemented with Tkinter and provides a native look across Windows, macOS, and Linux. It adapts to monitor DPI to ensure legibility and proper layout on both standard and high-resolution displays.

1.4 Technological Stack and Design Decisions

Core Language: Python 3.14 was chosen for rapid development, its ecosystem, and packaging with PyInstaller.

Database: SQLite with WAL mode is used for local deployments; PostgreSQL and MySQL drivers are available for multi-user deployments.

User Interface: Tkinter with ttk widgets provides a native look without external dependencies.

Security: bcrypt with cost factor 12 secures passwords; the system uses role-based access control.

Imaging: Pillow supports product photography and thumbnail generation.

Analytics: custom algorithms implement inventory health scoring, demand forecasting, and aging detection.

Deployment: PyInstaller packages the application into a single executable; `build.ps1` automates packaging. Recent builds produced a reproducible single-file executable (dist\CIS.exe) around 23.4–23.6 MB after optimization.

---

2. PROBLEM ANALYSIS AND JUSTIFICATION

2.1 Market Gap and Business Context

Computer parts retailers face several challenges that generic inventory systems do not address. Component obsolescence is rapid: inventory can lose market value within months. Pricing volatility in semiconductor markets can compress margins quickly. Suppliers vary in lead time and minimum order quantities, complicating restocking decisions. Small retailers also lack dedicated inventory analysts, so the system must provide quick insights via dashboards and alerts rather than deep analytic queries.

2.2 Specific Problems Addressed

The Inventory System addresses key operational pain points. It improves inventory accuracy through schema and transaction controls, reducing manual errors. Restocking intelligence predicts days-to-stockout using sales velocity so critical items are surfaced before depletion. Profit optimization is enabled by per-product margin calculations and recommendations for low-margin items. Aging inventory is detected by tracking days-in-inventory and flagging items beyond thresholds for clearance. The system implements role-based permissions and comprehensive audit logging for security and compliance. Finally, operational friction is reduced by single-file deployment, automatic database initialization, and an intuitive user experience requiring minimal training.

---

3. PROJECT OBJECTIVES

3.1 Primary Objectives

The project pursued four objectives. First, deliver an end-to-end inventory solution for product master data, stock tracking, sales recording, and reporting without external services. Second, embed business intelligence to compute metrics, flag anomalies, and provide data-driven recommendations. Third, ensure enterprise-grade security with encrypted password storage, RBAC, and audit logging. Fourth, maximize accessibility by enabling zero-infrastructure deployment as a single file that runs on minimal hardware.

3.2 Secondary Objectives

Secondary goals include extensibility via repository patterns and driver abstractions to support networked deployments, reliability through error handling and transaction management, compliance via audit trails and access controls, performance optimizations for large catalogs using indexed queries and pagination, and maintainability through clean architecture, testing, and documentation.

---

4. SYSTEM SCOPE AND LIMITATIONS

4.1 Scope Definition

The system manages product master data (SKU, name, brand, pricing, cost basis), real-time inventory tracking, and transaction recording for stock movements. Multi-user role-based access is supported (Admin, Manager, Staff). Business intelligence computes metrics such as profit margin, days-to-stockout, and aging detection. Audit logging records user activity with timestamps. The system supports single-machine SQLite deployments and server-backed PostgreSQL or MySQL for networked scenarios. It runs cross-platform using Python and Tkinter.

4.2 Technical Limitations

SQLite supports a single primary writer; WAL helps with concurrent reads, but deployments requiring 50+ simultaneous writers should migrate to PostgreSQL. Packaged executables include the Python runtime and can be large in constrained environments.

This release targets desktop platforms only. Mobile workflows and advanced time-series analytics are outside the current scope; existing BI uses rule-based methods rather than trained machine learning models.

---

5. ARCHITECTURE AND TECHNICAL DESIGN

5.1 System Architecture Overview

The architecture uses layered design: Presentation (Tkinter GUI), Business Logic (analytics and workflows), Data Access (repository pattern), Database drivers (SQLite, PostgreSQL, MySQL), and Security (authentication, authorization, password hashing, and audit logging).

5.2 Data Model and Database Schema

The data model includes Products, Users, Sales, Inventory, SerialNumbers, AuditLogs, and ProductImages. Products contain SKU, name, brand, pricing, cost, category, supplier links, and timestamps. Users store hashed passwords, roles, and login audit trails. Sales record transactions with timestamps and captured margins. Inventory maintains current quantities. SerialNumbers support unit-level tracking. AuditLogs record user actions. ProductImages reference product photos. Referential integrity and indexes optimize common queries.

5.3 Algorithm Design for Business Intelligence

Inventory Health Score: computed per-product as a composite of quantity status, aging, velocity, and margin health to yield a 0–100 score that prioritizes managerial attention.

Days-to-Stockout Prediction: analyzes recent sales velocity across a 30-day window to estimate depletion dates, applying conservative fallbacks when velocity is insufficient.

Aging Inventory Detection: flags items where last sale exceeds configurable thresholds (default 90 days), promoting clearance strategies.

All algorithms handle edge cases such as zero quantities or missing sales history gracefully.

---

6. IMPLEMENTATION AND TECHNICAL EXECUTION

6.1 Development Methodology

Development followed iterative, test-driven practices. Phases included requirements analysis, architecture design, implementation sprints, unit and integration testing (including background-task tests), QA with automated formatting and static analysis, performance tuning for large datasets, and deployment automation via `build.ps1` and PyInstaller.

6.2 Code Quality and Standards

The codebase uses automated tools to maintain quality: Black for formatting, Isort for imports, Flake8 and Pylint for static analysis, and type annotations for clarity. Error handling uses targeted try-except blocks and structured logging for production diagnostics.

6.3 Security Implementation

Security uses bcrypt (cost 12) for password hashing, RBAC for authorization, parameterized queries to prevent SQL injection, and audit logging for forensic tracing. Database transactions maintain ACID semantics for critical operations.

---

7. TESTING AND VALIDATION

7.1 Testing Strategy

Testing is multi-tiered. Unit tests validate repository CRUD operations and edge cases using temporary SQLite fixtures. Integration tests exercise end-to-end flows and UI persistence. Concurrency tests ensure thread-safe background tasks. Performance tests validate query optimization and pagination on large datasets.

7.2 Test Results

Automated tests validated core repository operations and background-task handling. The focused suite completed without failures in the development environment. Covered scenarios include CRUD operations, authentication, and thread-safe scheduling.

7.3 Code Quality Metrics

Static analysis and automated formatting are part of the continuous process and support maintainability. Test coverage emphasizes critical paths and deployment validations.

---

8. DEPLOYMENT AND OPERATIONS

8.1 Deployment Architecture

Supported deployment scenarios include single-machine desktop with SQLite, networked office using PostgreSQL for centralized data, and a future hybrid cloud architecture with PostgreSQL hosted remotely. The architecture allows migration from SQLite to server-backed databases without business logic changes.

8.2 Installation and Setup

Installation is simplified for non-technical users: download the executable, run it, and the application initializes the database and guides initial setup, including admin account creation and category configuration.

8.3 Performance Characteristics

Database and UI targets are conservative: product retrieval and inventory updates are optimized with indexes and WAL transactions. Typical UI operations are designed to be responsive on modest hardware. Storage is modest for large catalogs; packaged executables include the runtime.

---

9. RESULTS AND VALIDATION

9.1 Functional Validation

Core requirements were implemented and validated for exercised scenarios: product lifecycle management with referential integrity, real-time inventory tracking, multi-user RBAC, embedded BI for health scoring and aging detection, and comprehensive audit logging. Error handling recovers from database issues and logs diagnostic information.

Notable implementation and hardening items included in this revision are summarized below.

Export & Reporting: dashboard export and report generation were fixed and extended to include itemized receipts and a current-inventory section.

Modularization: shared dataclasses and configuration were moved to `core.py`; background execution was centralized in `utils/background_task.py`, and auxiliary repositories were organized in `utils/repositories_aux.py` to improve separation of concerns.

Point-of-sale improvements: the POS flow supports SKU or name lookup and clipboard helpers for faster entry.

Data normalization and persistence: categories were normalized during migration and save operations; deletion was hardened to ensure persistence and UI refresh even if auxiliary audit logging fails.

Security and first-run setup: removed seeded admin credentials and implemented a first-run admin creation flow to avoid default credentials in production.

Build and packaging: `build.ps1` was improved to use the project virtual environment, handle locked executable cases, and produce a reproducible single-file executable.

9.2 Non-Functional Requirements

The system meets non-functional requirements for usability, reliability, maintainability, security, and performance. Usability is focused on minimal training and clear error messages. Reliability is achieved through testing and defensive coding. Maintainability is supported by modular architecture and automated checks. Security follows best practices and includes audit trails. Performance targets are conservative and practical for the intended deployment scale.

---

10. CONCLUSIONS AND LESSONS LEARNED

10.1 Project Outcomes

The Inventory System demonstrates that enterprise-grade inventory management with embedded BI can be delivered as a single-file, zero-infrastructure solution. Small retailers can access powerful inventory analytics without complex IT setups.

Key achievements include functional completeness for core requirements, professional code quality practices, accessible deployment for non-technical users, extensibility toward multi-user scenarios, and reliability through testing and hardening.

10.2 Technical Lessons

Lessons learned include the adequacy of SQLite with WAL for single-machine deployments and the value of a layered architecture and repository pattern for backend flexibility. Embedded BI algorithms provide practical managerial value, and integrating security from design simplifies implementation. UI responsiveness and asynchronous operations significantly improve user experience.

10.3 Future Enhancements

Future work could include multi-location inventory, advanced analytics with trained models for demand forecasting, mobile applications for receiving and counts, cloud deployments with containerization, API integrations with accounting and supplier systems, and internationalization for multi-language support.

---

11. RECOMMENDATIONS

11.1 For Retailers and End-Users

Retailers should adopt digital inventory management to replace spreadsheets, which improves accuracy and reveals insights. Use BI outputs such as health scores and aging detection to guide decisions. Maintain disciplined data entry practices and review reports regularly.

11.2 For Developers and System Administrators

Adopt code review and testing practices to maintain quality. Implement backups even with SQLite, monitor database performance, and add indexes as needed. Conduct periodic security audits and maintain clear password and access policies.

11.3 For Academic and Research Contexts

The architecture offers a practical template for teaching repository patterns and layered design. Use this project as a case study combining business and technical requirements. Consider open-sourcing the project to enable community contributions and educational value.

---

12. REFERENCES

Python Software Foundation. (2024). Python 3.14 Documentation.
PyInstaller Contributors. (2024). PyInstaller Manual.
SQLite Consortium. (2024). SQLite Technical Documentation.
NIST Cybersecurity Framework. (2024). Recommendations for Password Hashing.
Brooks, F. P. (1995). The Mythical Man-Month: Essays on Software Engineering.
McConnell, S. (2004). Code Complete: A Practical Handbook of Software Construction.
Clean Code: A Handbook of Agile Software Craftsmanship, by Robert C. Martin.

---

13. APPENDICES

Appendix A: System Requirements

Hardware Requirements:
Windows 10/11, macOS 10.14+, or Linux (Ubuntu 18.04+). Approximately 200MB disk space is sufficient for moderate product catalogs. Memory recommendations start at 4GB, with 8GB recommended for catalogs approaching 100k products.

Software Requirements:
.NET Framework 4.5+ may be required for certain Windows components. Administrator privileges can be necessary during initial installation. An internet connection is required for downloading the executable.

Performance Expectations:
Typical interactive operations are designed for sub-second response. Large catalogs will have query times on the order of tens of milliseconds with appropriate indexing. Concurrent client expectations depend on backend: SQLite suits single-machine use; PostgreSQL supports higher concurrency.

Appendix B: Installation Instructions

1. Download Inventory_System.exe from the release repository.
2. Run the executable; the installer guides initial setup.
3. Launch the application from Start Menu or desktop shortcut.
4. Create the initial admin account when prompted and configure categories and suppliers.
5. Begin entering inventory.

The application initializes the database automatically.

Appendix C: Data Backup Procedures

Implement daily backups to protect against data loss. Strategies include local copies to external media, cloud sync to services such as Google Drive or OneDrive, and automated PowerShell backups scheduled during off-hours. A recommended frequency is daily after business hours.

Appendix D: Source Code Statistics

Approximate statistics: total lines of code around 4,700, over 250 functions, and 40+ classes. Test coverage emphasizes critical paths with focused automated tests. Documentation includes extensive docstrings and comments. The development build produced a ~23.4–23.6MB executable. Major repository implementations include ProductRepository, UserRepository, AuditRepository, and SalesHistoryRepository. Database drivers support SQLite, PostgreSQL, and MySQL.

---

ACKNOWLEDGMENTS

This project represents the culmination of academic study in software engineering, database design, and business analysis. Gratitude is extended to:

Professor Modesto C. Tarrazona for guidance and feedback throughout development, shaping requirements and validating implementation approach.

Course IT5L (2868) Cohort for iterative testing, use case validation, and constructive feedback improving system usability.

Open-Source Community for exceptional tools—Python, SQLite, Tkinter, PyInstaller—enabling portable, capable system development without licensing costs.

Computer Parts Retailers who shared operational insights enabling authentic problem definition ensuring system solves real business challenges.

---

This thesis documents software engineering principles applied to authentic business problems. The Inventory System shows how design, testing, and user-centric development create practical tools for retailers. May this work inspire future developers to solve real problems that improve business operations and support communities.

Final Status: Complete and Ready for Deployment
Date of Completion: March 2026
System Version: 1.0.0
Quality Assurance: Comprehensive testing validated
Performance Validation: Production-ready performance characteristics confirmed
