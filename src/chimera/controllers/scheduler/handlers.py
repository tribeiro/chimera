from chimera.core.exceptions import ProgramExecutionException, printException
from chimera.controllers.imageserver.imagerequest import ImageRequest

import copy

def requires(instrument):
    """Simple dependecy injection mechanism. See ProgramExecutor"""

    def requires_deco(func):
        if hasattr(func, "__requires__"):
            func.__requires__.append(instrument)
        else:
            func.__requires__ = [instrument]
        return func
    
    return requires_deco

class ActionHandler(object):

    @staticmethod
    def process(action):
        pass

    @staticmethod
    def abort(action):
        pass

    @staticmethod
    def log(action):
        return str(action)

class PointHandler(ActionHandler):

    @staticmethod
    @requires("telescope")
    @requires("dome")
    def process(action):
        telescope = PointHandler.telescope
        dome = PointHandler.dome

        try:
            # First slew telescope to given position (or none)
            if action.targetRaDec is not None:
                telescope.slewToRaDec(action.targetRaDec)
            elif action.targetAltAz is not None:
                telescope.slewToAltAz(action.targetAltAz)
            elif action.targetName is not None:
                telescope.slewToObject(action.targetName)

            # After slewing apply any given offset
            if action.offsetNS is not None:
                if action.offsetNS.AS > 0.:
                    telescope.moveNorth(action.offsetNS.AS)
                else:
                    telescope.moveSouth(-action.offsetNS.AS)

            if action.offsetEW is not None:
                if action.offsetEW.AS > 0.:
                    telescope.moveWest(action.offsetEW.AS)
                else:
                    telescope.moveEast(-action.offsetEW.AS)

        except Exception, e:
            raise ProgramExecutionException(str(e))

    @staticmethod
    def abort(action):
        # use newer Proxies as Proxies cannot be shared between threads
        telescope = copy.copy(PointHandler.telescope)
        dome = copy.copy(PointHandler.dome)

        telescope.abortSlew()
        dome.abortSlew()
        
    @staticmethod
    def log(action):

        offsetNS_str = '' if action.offsetNS is None else ' north %s' % action.offsetNS \
            if action.offsetNS > 0 else ' south %s' % action.offsetNS
        offsetEW_str = '' if action.offsetEW is None else ' west %s' % action.offsetEW \
            if action.offsetEW > 0 else ' east %s' % action.offsetNS

        offset = '' if action.offsetNS is None and action.offsetEW is None else ' offset:%s%s' % (offsetNS_str,
                                                                                                  offsetEW_str)

        if action.targetRaDec is not None:
            return "slewing telescope to (ra dec) %s%s" % (action.targetRaDec, offset)
        elif action.targetAltAz is not None:
            return "slewing telescope to (alt az) %s%s" % (action.targetAltAz, offset)
        elif action.targetName is not None:
            return "slewing telescope to (object) %s%s" % (action.targetName, offset)
        else:
            return "applying telescope%s" % offset

class ExposeHandler(ActionHandler):

    @staticmethod
    @requires("camera")
    @requires("filterwheel")
    def process(action):

        camera = ExposeHandler.camera
        try:
            filterwheel = ExposeHandler.filterwheel
        except:
            filterwheel = camera


        # not considered in abort handling (should be fast enough to wait!)
        if action.filter is not None:
            try:
                filterwheel.setFilter(str(action.filter))
            except:
                pass
            
        ir = ImageRequest(frames   = int(action.frames),
                          exptime  = float(action.exptime),
                          shutter  = str(action.shutter),
                          type     = str(action.imageType),
                          filename = str(action.filename),
                          object_name = str(action.objectName),
                          window = action.window,
                          binning = action.binning,
                          wait_dome = True)

        ir.headers += [("PROGRAM", str(action.program.name), "Program Name"),
                       ("PROG_PI", str(action.program.pi), "Principal Investigator")]

        try:
            camera.expose(ir)
        except Exception, e:
            printException(e)
            raise ProgramExecutionException("Error while exposing")

    @staticmethod
    def abort(action):
        camera = copy.copy(ExposeHandler.camera)
        camera.abortExposure()

    @staticmethod
    def log(action):
        return "exposing: filter=%s exptime=%s frames=%s type=%s" % (str(action.filter),
                                                                     str(action.exptime),
                                                                     str(action.frames),
                                                                     str(action.imageType))

class AutoFocusHandler(ActionHandler):

    @staticmethod
    @requires("autofocus")
    def process(action):
        autofocus = AutoFocusHandler.autofocus

        try:
            # TODO: filter=action.filter,
            autofocus.focus (filter=action.filter,
                             exptime=action.exptime,
                             binning=action.binning,
                             window=action.window,
                             start=action.start,
                             end=action.end,
                             step=action.step)
        except Exception, e:
            printException(e)
            raise ProgramExecutionException("Error while autofocusing")

    @staticmethod
    def abort(action):
        pass

class AutoFlatHandler(ActionHandler):

    @staticmethod
    @requires("autoflat")
    def process(action):
        autoflat = AutoFlatHandler.autoflat

        try:
            autoflat.getFlats(action.filter, n_flats=action.frames)
        except Exception, e:
            printException(e)
            raise ProgramExecutionException("Error trying to take flats")

    @staticmethod
    def abort(action):
        skyflat = copy.copy(AutoFlatHandler.autoflat)
        skyflat.abort()

class PointVerifyHandler(ActionHandler):

    @staticmethod
    @requires("point_verify")
    def process(action):

        # FIXME: better pv interface
        pv = PointVerifyHandler.point_verify

        try:
            if action.here is not None:
                pv.pointVerify()
            elif action.choose is not None:
                pv.choose()
        except Exception, e:
            raise ProgramExecutionException(str(e))

    @staticmethod
    def abort(action):
        pass
        

