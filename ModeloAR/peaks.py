import numpy as np
import pandas as pd

def importado():
    print("Se ejecuta modelo!")

def scpa(time, sensor, n, t): # Saca los n peaks mas altos y selecciona los t/2 siguientes y t/2 anteriores.
    ind = np.argsort(np.absolute(sensor))[::-1] # Ordenando los valores. Probar con valor absoluto.
    #print(ind[:4])
    countn = 0
    search = []
    norep = [0]*len(time)
    norepflag = False
    for start in ind:
        norepflag = False
        i = start
        target1 = time[i] - np.timedelta64(t//2,'s')
        i = start
        target2 = time[i] + np.timedelta64(t//2,'s')
        aux = []
        i = start
        #print(i)
        while(i >= 0 and i < len(time) - 1 and time[i] > target1 and norepflag == False):
            #print(time[i])
            aux.append(i)
            if(norep[i] == 0):
                norep[i] = 1
            else:
                norepflag = True
            i -= 1
        if(norepflag == True):
            continue
        i = start + 1
        aux = aux[::-1]
        while(i < len(time) - 1 and i >= 0 and time[i] < target2 and norepflag == False):
            #print(time[i])
            aux.append(i)
            if(norep[i] == 0):
                norep[i] = 1
            else:
                norepflag = True
            i += 1
        if(norepflag == False):
            search.append(aux)
            countn += 1
        if(countn >= n):
            break
    return search

def sdpa(time, sensor, n, t): # Saca los n peaks mas altos y selecciona los t siguientes.
    ind = np.argsort(np.absolute(sensor))[::-1]  # Ordenando los valores.
    #print(ind[:4])
    countn = 0
    search = []
    norep = [0]*len(time)
    norepflag = False
    for start in ind:
        norepflag = False
        i = start
        target = time[i] + np.timedelta64(t,'s')
        aux = []
        #print(i)
        while(time[i] < target and i < len(time) - 1 and norepflag == False):
            #print(time[i])
            aux.append(i)
            if(norep[i] == 0):
                norep[i] = 1
            else:
                norepflag = True
            i += 1
        if(norepflag == False):
            search.append(aux)
            countn += 1
        if(countn >= n):
            break
    return search


def smaxe(time, sensor, n, t): # Selecciona los n peaks de energia mas altos entre t tiempos.
    target = time[0] + np.timedelta64(t,'s')
    a = 0           #inicio de la integral
    b = 0           #final de la integral
    ivalue = 0       #ivalue de la integral
    while(time[b] < target and b < len(time) - 1): #Se obtiene el primer valor de la integral y el largo en indices, dado un t.
        ivalue += abs(sensor[b])**2
        b += 1
    res = []
    res.append([a,b,ivalue])
    for a in range(0, len(sensor)):
        ivalue -= abs(sensor[a])**2
        #a += 1
        b += 1
        if b >= len(sensor):
            break
        ivalue += abs(sensor[b])**2
        res.append([a,b,ivalue])
    ressort = sorted(res,key=lambda x: x[2])[::-1]
    ret = []
    ret.append(ressort[0])
    cont = 1
    for i in ressort:
        add = True
        #print(i)
        for k in ret:
            if(k[0] <= i[1] and k[0] >= i[0] or k[1] >= i[0] and k[1] <= i[1]):
                add = False
        if(add == True):
            ret.append(i)
            cont += 1
        if(cont >= n):
            break
    return ret 


def smine(time, sensor, n, t): # Selecciona los n peaks de energia mas altos entre t tiempos.
    target = time[0] + np.timedelta64(t,'s')
    a = 0           #inicio de la integral
    b = 0           #final de la integral
    ivalue = 0       #ivalue de la integral
    while(time[b] < target and b < len(time) - 1): #Se obtiene el primer ivalue de la integral y el largo en indices, dado un t.
        ivalue += abs(sensor[b])**2
        b += 1
    res = []
    res.append([a,b,ivalue])
    for a in range(0, len(sensor)):
        ivalue -= abs(sensor[a])**2
        #a += 1
        b += 1
        if b >= len(sensor):
            break
        ivalue += abs(sensor[b])**2
        res.append([a,b,ivalue])
    ressort = sorted(res,key=lambda x: x[2])
    ret= []
    ret.append(ressort[0])
    cont = 1
    for i in ressort:
        add = True
        #print(i)
        for k in ret:
            if(k[0] <= i[1] and k[0] >= i[0] or k[1] >= i[0] and k[1] <= i[1]):
                add = False
        if(add == True):
            ret.append(i)
            cont += 1
        if(cont >= n):
            break
    return ret 



