"""Image quality stage wrapper."""

from app.services.image_quality import assess_image_quality


def assess_page_quality(img):
    return assess_image_quality(img)
