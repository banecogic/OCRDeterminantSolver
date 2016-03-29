# -*- coding: utf-8 -*-
"""
@author: Branislav Cogic
"""

import numpy as np
import math
import cv2 as cv2
import matplotlib.pyplot as plt
import scipy as sc
import collections
from scipy.spatial import distance
from sklearn.cluster import KMeans

def nadji_konture_determinante(pogodne_konture, frame_bin, frame, prolaz):
    potencijalne_granice_determinante = []
    rbr = 0
    for contour in pogodne_konture:
        rotated_contour = rotate_contour(contour, frame_bin)
        rbr = rbr+1
        x,y,w,h = cv2.boundingRect(rotated_contour) #koordinate i velicina granicnog pravougaonika
        #area = cv2.contourArea(contour)
        rect = cv2.minAreaRect(contour)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        cv2.drawContours(frame, [box], 0, (0,0,255), 2)
        rect = cv2.minAreaRect(rotated_contour)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        cv2.drawContours(frame, [box], 0, (0,255,255), 2)
        if (h/w > 5) and h>30 and w>5:
            potencijalne_granice_determinante.append(contour)
            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            cv2.drawContours(frame, [box], 0, (0,255,0), 2)
            
    print "Broj potencijalnih granica pre mergovanja = ", len(potencijalne_granice_determinante)
    potencijalne_granice_determinante = merge_regions(potencijalne_granice_determinante)
    potencijalne_granice_determinante = merge_intersected(potencijalne_granice_determinante)
    print "Broj potencijalnih granica nakon mergovanja = ", len(potencijalne_granice_determinante)
    if len(potencijalne_granice_determinante) != 2:
        return
        
    # NALAZENJE PRAVOUGAONIKA KOJI PREDSTALJVA REGION DETERMINANTE
    granica_determinante = np.ndarray((len(potencijalne_granice_determinante[0])+len(potencijalne_granice_determinante[1]), 1,2), dtype=np.int32)
    granica_determinante = np.concatenate((potencijalne_granice_determinante[0], potencijalne_granice_determinante[1]))    
    rectDet = cv2.minAreaRect(granica_determinante)
    boxDet = cv2.boxPoints(rectDet)
    boxDet = np.int0(boxDet)
    cv2.drawContours(frame, [boxDet], 0, (255,0,0), 2)
    konture_determinante = []
    konture_unutar_determinante = []
    
    rotirane_konture_mapa_po_x = {}
    for contour in pogodne_konture:
        #rotated_contour = rotate_contour(contour, frame_bin)
        #x,y,w,h = cv2.boundingRect(rotated_contour) #koordinate i velicina granicnog pravougaonika
        #area = cv2.contourArea(contour)
        rectCont = cv2.minAreaRect(contour)
        centerCont, sizeCont, angleCont = rectCont
        x,y = centerCont
        indicator, vertices = cv2.rotatedRectangleIntersection(rectDet, rectCont)
        print "Indikator presecnosti: ", indicator
        if indicator>0:
            konture_determinante.append(contour)
        if indicator == 2:
            konture_unutar_determinante.append(contour)
            rotirane_konture_mapa_po_x[x] = contour
    sortirane_rotirane_mapa_po_x = collections.OrderedDict(sorted(rotirane_konture_mapa_po_x.items()))
    sortirane_rotirane_konture = np.array(sortirane_rotirane_mapa_po_x.values())
    iscrtajIzKontureSliku(sortirane_rotirane_konture, frame_bin, prolaz)
            
    print "Prepoznate konture determinante: ", len(konture_determinante)
    print "Prepoznate sortirane konture unutar determinante: ", len(sortirane_rotirane_konture)
    # Rotiranje kontura unutar determinante oko centra determinante
    centerDet, sizeDet, angleDet = cv2.minAreaRect(granica_determinante)
    print "Centar determinante je u    :   ", centerDet
    rotirane_konture = []
    distances_x = []
    distances_y = []
    for contour in sortirane_rotirane_konture:
        xt,yt,h,w = cv2.boundingRect(contour)
        rectCont = cv2.minAreaRect(contour)
        centerCont, sizeCont, angleCont = rectCont
        region_points = []
        for i in range (xt,xt+h):
            for j in range(yt,yt+w):
                dist = cv2.pointPolygonTest(contour,(i,j),False)
                if dist>=0 and frame_bin[j,i]==255: # da li se tacka nalazi unutar konture?
                    region_points.append([i,j])
        cdx,cdy = centerDet
#        height, width = sizeCont
#        if width<height:
#            angle+=90
        # Rotiranje svake tačke regiona oko centra rotacije
        alpha = np.pi/2 - abs(np.radians(angleDet))
        region_points_rotated = np.ndarray((len(region_points), 1,2), dtype=np.int32)
        for i, point in enumerate(region_points):
            x = point[0]
            y = point[1]
            
            #TODO 1 - izračunati koordinate tačke nakon rotacije
            rx = np.sin(alpha)*(x-cdx) - np.cos(alpha)*(y-cdy) + cdx
            ry = np.cos(alpha)*(x-cdx) + np.sin(alpha)*(y-cdy) + cdy
            region_points_rotated[i] = [rx,ry]
        rectRotatedCont = cv2.minAreaRect(region_points_rotated)
        centerRotatedCont, sizeRotatedCont, angleRotatedCont = rectRotatedCont
        crcx, crcy = centerRotatedCont
        distances_x.append(crcx-cdx)
        distances_y.append(crcy-cdy)
        boxRotatedCont = cv2.boxPoints(rectRotatedCont)
        print "Temena rotiranog regiona: ", boxRotatedCont
        boxRotatedCont = np.int0(boxRotatedCont)
        cv2.drawContours(frame, [boxRotatedCont], 0, (255,255,255), 2)
        rotirane_konture.append(region_points_rotated)
        rotirane_konture_mapa_po_x[int(crcx)] = region_points_rotated
    sortirane_rotirane_mapa_po_x = collections.OrderedDict(sorted(rotirane_konture_mapa_po_x.items()))
    sortirane_rotirane_konture = np.array(sortirane_rotirane_mapa_po_x.values())
    print "Broj kontura u determinanti = ", len(konture_unutar_determinante), " sortiranih treba isto? = ", len(sortirane_rotirane_konture)
    
    # KMeans razdvajanje brojeva po pripadnosti vrsti i koloni
    n_clusters = int(round(math.sqrt(len(konture_unutar_determinante)), 0))
    print "Dimenzija determinante ", n_clusters, "x", n_clusters
    # KMeans za razdvajanje vrsta
    print "Distance po x od centra determinante : ", distances_x
    k_means_x = KMeans(n_clusters=n_clusters, max_iter=1000)
    distances_x = np.array(distances_x).reshape(len(distances_x), 1)
    k_means_x.fit(distances_x)
    print "ZA X DIMENZIJU: KMeans labels_ : ", k_means_x.labels_
    print "ZA X DIMENZIJU: KMeans cluster_centers_ :", k_means_x.cluster_centers_
    
    # KMeans za razdvajanje kolona
    print "Distance po y od centra determinante : ", distances_y
    k_means_y = KMeans(n_clusters=n_clusters, max_iter=1000)
    distances_y = np.array(distances_y).reshape(len(distances_y), 1)
    k_means_y.fit(distances_y)
    print "ZA Y DIMENZIJU: KMeans labels_ : ", k_means_y.labels_
    print "ZA Y DIMENZIJU: KMeans cluster_centers_ :", k_means_y.cluster_centers_
    
def merge_intersected(contours):
    ret_val = []
    merged_index = [] #lista indeksa kontura koje su već spojene sa nekim
    
    for i,contour1 in enumerate(contours): #slova
        if i in merged_index:
            continue
        rect1 = cv2.minAreaRect(contour1)
        for j,contour2 in enumerate(contours): #kukice
            if j in merged_index or i == j:
                continue
            rect2 = cv2.minAreaRect(contour2)
            
            #TODO 2 - izvršiti spajanje kukica iznad slova
            #spajanje dva niza je moguće obaviti funkcijom np.concatenate((contour1,contour2))
            indicator, vertices = cv2.rotatedRectangleIntersection(rect1, rect2)
            if indicator>0:
                #spajanje kontura
                ret_val.append(np.concatenate((contour1,contour2)))
                merged_index.append(i)
                merged_index.append(j)
    #svi regioni koji se nisu ni sa kim spojili idu u listu kontura, bez spajanja
    for idx,contour in enumerate(contours):
        if idx not in merged_index:
            ret_val.append(contour)
        
    return ret_val
    
def rotate_contour(contour, frame_bin):
    center, size, angle = cv2.minAreaRect(contour)
    xt,yt,h,w = cv2.boundingRect(contour)
    region_points = []
    for i in range (xt,xt+h):
        for j in range(yt,yt+w):
            dist = cv2.pointPolygonTest(contour,(i,j),False)
            if dist>=0 and frame_bin[j,i]==255: # da li se tacka nalazi unutar konture?
                region_points.append([i,j])
    cx,cy = center
    height, width = size
    if width<height:
        angle-=90
    # Rotiranje svake tačke regiona oko centra rotacije
    alpha = np.pi/2 - abs(np.radians(angle))
    region_points_rotated = np.ndarray((len(region_points), 1,2), dtype=np.int32)
    for i, point in enumerate(region_points):
        x = point[0]
        y = point[1]
        
        #TODO 1 - izračunati koordinate tačke nakon rotacije
        rx = np.sin(alpha)*(x-cx) - np.cos(alpha)*(y-cy) + cx
        ry = np.cos(alpha)*(x-cx) + np.sin(alpha)*(y-cy) + cy
        region_points_rotated[i] = [rx,ry]
    return region_points_rotated

def iscrtajIzKontureSliku(contours, image_bin, prolaz):
    if prolaz != 5:
        return
    for contour in contours:
        x,y,w,h = cv2.boundingRect(contour)
        region = image_bin[y:y+h+1,x:x+w+1]
        plt.figure()
        plt.imshow(region, 'gray')
    
def izaberi_konture(contour_borders, bin_image):
    pogodne_konture = []
    ### PRVO NADJEMO USPRAVNE LINIJE
    #for contour in contour_borders:
    #    x,y,w,h = cv2.boundingRect(contour) #koordinate i velicina granicnog pravougaonika
    #    area = cv2.contourArea(contour)
        
    
    for contour in contour_borders:
        x,y,w,h = cv2.boundingRect(contour) #koordinate i velicina granicnog pravougaonika
        area = cv2.contourArea(contour)
        
        # PRONACI REGIONE KOJI PREDSTAVLJAJU USPRAVNE LINIJE DETERMINANTE
        if (h/w > 3):
            pogodne_konture.append(contour)
            print "LAJNA H > 3 * W"
            
        # PRONACI REGIONE IZMEDJU LINIJA 
        
        # ZA SLOVA
        elif area > 20 and area < 10000 and h < 400 and h > 10 and w > 10 and w<400:
            pogodne_konture.append(contour)
        # ZA GRANICE DETERMINANTE
        #elif area > 10 and h>50 and h< 400 and w<20:
        #    pogodne_konture.append(contour)
    pogodne_konture = merge_regions(pogodne_konture)
    return pogodne_konture
    
def merge_regions(contours):
    '''Funkcija koja vrši spajanje kukica i kvačica sa osnovnim karakterima
    Args:
        contours: skup svih kontura (kontura - niz tacaka bele boje)
    Return:
        ret_val: skup kontura sa spojenim kukicama i kvacicama'''
    ret_val = []
    merged_index = [] #lista indeksa kontura koje su već spojene sa nekim
    
    for i,contour1 in enumerate(contours): #slova
        if i in merged_index:
            continue
        min_x1 = min(contour1[:,0,0])
        max_x1 = max(contour1[:,0,0])
        min_y1 = min(contour1[:,0,1])
        max_y1 = max(contour1[:,0,1])
        for j,contour2 in enumerate(contours): #kukice
            if j in merged_index or i == j:
                continue
            min_x2 = min(contour2[:,0,0])
            max_x2 = max(contour2[:,0,0])
            min_y2 = min(contour2[:,0,1])
            max_y2 = max(contour2[:,0,1])
            
            #TODO 2 - izvršiti spajanje kukica iznad slova
            #spajanje dva niza je moguće obaviti funkcijom np.concatenate((contour1,contour2))
            if (min_y1<min_y2) and (max_y1>max_y2) and (min_x1<min_x2) and (max_x1>max_x2):
                #spajanje kontura
                ret_val.append(np.concatenate((contour1,contour2)))
                merged_index.append(i)
                merged_index.append(j)
    #svi regioni koji se nisu ni sa kim spojili idu u listu kontura, bez spajanja
    for idx,contour in enumerate(contours):
        if idx not in merged_index:
            ret_val.append(contour)
        
    return ret_val
    
def crtaj_konture(contours, frame, frame_bin):
    regions_dic = {}
    for contour in contours:
        x,y,w,h = cv2.boundingRect(contour) #koordinate i velicina granicnog pravougaonika
        region = frame_bin[y:y+h+1,x:x+w+1];
        #regions_dic[x] = cv2.resize(region,(28,28), interpolation = cv2.INTER_LANCZOS4)
        cv2.drawContours(frame, contour, -1, (0,0,255), 2)
        cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)

def regioni_od_interesa(frame, frame_bin, prolaz):
    img, contour_borders, hierarchy = cv2.findContours(frame_bin.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    print "Prepoznate konture od cv2 biblioteke: ", len(contour_borders)
    #iscrtajIzKontureSliku(contour_borders, img)
    izabrane_konture = izaberi_konture(contour_borders, frame_bin)
    print "Prepoznate izabrane konture: ", len(izabrane_konture)
    spojene_izabrane_konture = merge_regions(izabrane_konture)
    print "Prepoznate spojene izabrane konture: ", len(spojene_izabrane_konture)
    spojene_presecne_izabrane_konture = merge_intersected(spojene_izabrane_konture)
    print "Prepoznate spojene i presecne izabrane konture: ", len(spojene_presecne_izabrane_konture)
    #crtaj_konture(contours, frame, frame_bin)
    sorted_regions = [] # lista sortiranih regiona po x osi (sa leva na desno)
    #contours2, contour_angles, contour_centers, contour_sizes = centri_uglovi_velicine(contours, frame_bin)
    #rotated_contours = []
    #rotated_contours = rotate_regions(contours2, contour_angles, contour_centers, contour_sizes)
    determinant_contours = nadji_konture_determinante(spojene_presecne_izabrane_konture, frame_bin, frame, prolaz)
    #crtaj_konture(rotated_contours, frame, frame_bin)
    
    #sorted_regions_dic = collections.OrderedDict(sorted(regions_dic.items()))
    #sorted_regions = sorted_regions_dic.values()
    return frame, sorted_regions
    
# Rotiranje regiona
def rotate_regions(contours,angles,centers,sizes):
    '''Funkcija koja vrši rotiranje regiona oko njihovih centralnih tačaka
    Args:
        contours: skup svih kontura [kontura1, kontura2, ..., konturaN]
        angles:   skup svih uglova nagiba kontura [nagib1, nagib2, ..., nagibN]
        centers:  skup svih centara minimalnih pravougaonika koji su opisani 
                  oko kontura [centar1, centar2, ..., centarN]
        sizes:    skup parova (height,width) koji predstavljaju duzine stranica minimalnog
                  pravougaonika koji je opisan oko konture [(h1,w1), (h2,w2), ...,(hN,wN)]
    Return:
        ret_val: rotirane konture'''
    ret_val = []
    for idx, contour in enumerate(contours):
        angle = angles[idx]
        cx,cy = centers[idx]
        height, width = sizes[idx]
        if width<height:
            angle+=90
            
        # Rotiranje svake tačke regiona oko centra rotacije
        alpha = np.pi/2 - abs(np.radians(angle))
        region_points_rotated = np.ndarray((len(contour), 1,2), dtype=np.int32)
        for i, point in enumerate(contour):
            x = point[0]
            y = point[1]
            
            #TODO 1 - izračunati koordinate tačke nakon rotacije
            rx = np.sin(alpha)*(x-cx) - np.cos(alpha)*(y-cy) + cx
            ry = np.cos(alpha)*(x-cx) + np.sin(alpha)*(y-cy) + cy
            region_points_rotated[i] = [rx,ry]
        ret_val.append(region_points_rotated)
    #print ret_val
    return ret_val
    
def centri_uglovi_velicine(contour_borders, frame_bin):
    contours = []
    contour_angles = []
    contour_centers = []
    contour_sizes = []
    for contour in contour_borders:
        center, size, angle = cv2.minAreaRect(contour)
        xt,yt,h,w = cv2.boundingRect(contour)
        region_points = []
        for i in range (xt,xt+h):
            for j in range(yt,yt+w):
                dist = cv2.pointPolygonTest(contour,(i,j),False)
                if dist>=0 and frame_bin[j,i]==255: # da li se tacka nalazi unutar konture?
                    region_points.append([i,j])
        contour_centers.append(center)
        contour_angles.append(angle)
        contour_sizes.append(size)
        contours.append(region_points)
    return contours, contour_angles, contour_centers, contour_sizes