import datetime
from backend.app.db.session import SessionLocal, engine, Base
from backend.app.db.models import HCP, Product

def seed_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(HCP).count() > 0:
            print("Database already seeded.")
            return

        # Seed HCPs
        hcps = [
            HCP(
                name="Dr. Ananya Sharma",
                specialty="Cardiology",
                email="ananya.sharma@hospital.com",
                phone="+91 98765 43210",
                address="Apollo Cardiology Center, New Delhi"
            ),
            HCP(
                name="Dr. Rajesh Patel",
                specialty="Endocrinology",
                email="rajesh.patel@clinic.com",
                phone="+91 98123 45678",
                address="Diabetes Care Clinic, Mumbai"
            ),
            HCP(
                name="Dr. Amit Verma",
                specialty="General Medicine",
                email="amit.verma@health.org",
                phone="+91 99988 77766",
                address="Verma Clinic, Bangalore"
            ),
            HCP(
                name="Dr. Priya Nair",
                specialty="Pediatrics",
                email="priya.nair@kidshealth.com",
                phone="+91 97766 55443",
                address="Children's Hospital, Chennai"
            ),
            HCP(
                name="Dr. Vikram Seth",
                specialty="Oncology",
                email="vikram.seth@cancerinstitute.com",
                phone="+91 91122 33445",
                address="Seth Cancer Institute, Hyderabad"
            )
        ]
        
        # Seed Products
        products = [
            Product(
                name="CardioX",
                therapeutic_area="Cardiology",
                description="Advanced beta-blocker for hypertension management"
            ),
            Product(
                name="Diabeta",
                therapeutic_area="Endocrinology",
                description="Next-gen oral hypoglycemic agent for Type-2 Diabetes"
            ),
            Product(
                name="LipiMed",
                therapeutic_area="Cardiology",
                description="High-potency statin for hypercholesterolemia control"
            ),
            Product(
                name="Asthmax",
                therapeutic_area="Pulmonology",
                description="Fast-acting bronchodilator inhaler"
            ),
            Product(
                name="NeuroMax",
                therapeutic_area="Neurology",
                description="Neuroprotective supplement for cognitive support"
            )
        ]
        
        db.add_all(hcps)
        db.add_all(products)
        db.commit()
        print("Database seeded successfully with HCPs and Products!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
