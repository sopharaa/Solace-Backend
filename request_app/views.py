from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Request
from .serializers import RequestSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_requests(request):
    requests = Request.objects.all().order_by('-created_at')
    serializer = RequestSerializer(requests, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_request(request):
    serializer = RequestSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user_id=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def respond_request(request, uuid):
    try:
        req = Request.objects.get(uuid=uuid)
    except Request.DoesNotExist:
        return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
        
    req_status = request.data.get('status')
    if req_status not in [Request.Status.APPROVED, Request.Status.REJECTED]:
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
    req.status = req_status
    req.save()
    
    serializer = RequestSerializer(req)
    return Response(serializer.data, status=status.HTTP_200_OK)
