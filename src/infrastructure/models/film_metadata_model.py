from sqlalchemy import Column, BigInteger, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from infrastructure.databases.base import Base

class SubmissionFilmMetadataModel(Base):
    """
    Bảng lưu trữ thông số kỹ thuật ảnh phim đặc thù:
    Cuộn phim (film_stock), ISO, Camera body, Lens, Lab tráng rửa, Máy scan, Quy trình tráng (development_process)
    """
    __tablename__ = 'submission_film_metadata'
    __table_args__ = {'extend_existing': True}

    submission_id = Column(BigInteger, ForeignKey('submissions.id', ondelete='CASCADE'), primary_key=True)
    film_stock = Column(String(100), nullable=False) # Vd: Kodak Portra 400, Fuji C200
    film_iso = Column(Integer, nullable=True)         # Vd: 100, 200, 400, 800
    camera_body = Column(String(100), nullable=True) # Vd: Leica M6, Canon AE-1, Nikon FM2
    lens = Column(String(100), nullable=True)        # Vd: 50mm f/1.4, 35mm f/2
    lab_name = Column(String(150), nullable=True)    # Vd: LLab Studio, Zone5 Darkroom
    scanner_info = Column(String(150), nullable=True)# Vd: Fuji Frontier SP3000
    development_process = Column(String(50), default='C-41') # C-41, B&W, E-6, Push/Pull
    taken_at_location = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
